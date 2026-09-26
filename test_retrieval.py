"""Behavioral tests run without downloading models or contacting providers."""
import json
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from engine import Engine, generate
from retrieval import select_evidence, laya_rank, semantic_search


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        rows = [dict(chunk_id=str(i), text=text) for i, text in enumerate([
            'Cocaína: efectos y mecanismo.', 'La conservación de la muestra requiere frío.',
            'Otro documento sobre muestras.', 'Una relación incidental.'])]
        self.engine = SimpleNamespace(rows=rows, byid={r['chunk_id']: r for r in rows})

    def test_semantic_only_passage_can_reach_generator(self):
        with patch('retrieval.semantic_search', return_value=[('1', .91)]):
            ids, _, diag = select_evidence(self.engine, '¿Cómo guardar la muestra?', [4, 0, 0, 0], [], 2, False)
        self.assertIn('1', ids)
        self.assertTrue(diag['semantic_used'])

    def test_graph_does_not_displace_stronger_direct_evidence(self):
        with patch('retrieval.semantic_search', return_value=[]):
            ids, _, _ = select_evidence(self.engine, 'muestras', [4, 3, 2, 0],
                                        [{'chunk_id': '3'}], 2, False)
        self.assertEqual(ids, ['0', '1'])

    def test_reranker_can_promote_low_lexical_candidate_and_keeps_provenance(self):
        judgments = {'0': {'relevance': 'irrelevante', 'laya_score': .1},
                     '1': {'relevance': 'directa', 'laya_score': .9}}
        with patch('retrieval.semantic_search', return_value=[('1', .92)]), \
             patch('retrieval.laya_rank', return_value=judgments):
            ids, meta, diag = select_evidence(self.engine, 'conservación', [4, 1, 0, 0], [], 1, True)
        self.assertEqual(ids, ['1'])
        self.assertEqual(meta['1']['relevance'], 'directa')
        self.assertEqual(len(diag['candidate_ids']), 2)
        self.assertTrue(diag['laya_used'])

    def test_model_failure_is_visible_and_keeps_lexical_results(self):
        with patch('retrieval.semantic_search', side_effect=RuntimeError('offline')), \
             patch('retrieval.laya_rank', side_effect=RuntimeError('missing')), \
             self.assertLogs('retrieval', level='ERROR'):
            ids, _, diag = select_evidence(self.engine, 'muestra', [3, 2, 0, 0], [], 2, True)
        self.assertEqual(ids, ['0', '1'])
        self.assertEqual(len(diag['warnings']), 2)
        self.assertFalse(diag['laya_used'])

    def test_pilot_keeps_strong_lexical_evidence_despite_bad_laya_judgment(self):
        judgments = {str(i): {'relevance': 'directa', 'laya_score': i / 4}
                     for i in range(4)}
        with patch('retrieval.semantic_search', return_value=[]), \
             patch('retrieval.laya_rank', return_value=judgments):
            ids, _, diag = select_evidence(self.engine, 'conservación', [4, 3, 2, 1], [], 6, True)
        self.assertEqual(ids[:2], ['0', '1'])
        self.assertEqual(diag['protected_ids'], ['0', '1'])

    def test_weak_semantic_matches_do_not_force_an_answer(self):
        with patch('retrieval.semantic_search', return_value=[('0', .99)]) as semantic, \
             patch('retrieval.laya_rank') as rank:
            ids, _, _ = select_evidence(self.engine, 'horarios de trenes', [0]*4, [], 2, True)
        self.assertEqual(ids, [])
        semantic.assert_not_called()
        rank.assert_not_called()

    def test_malformed_laya_result_falls_back_without_partial_reordering(self):
        with patch('retrieval.semantic_search', return_value=[]), \
             patch('retrieval.laya_rank', return_value={'1': {'laya_score': 1}}), \
             self.assertLogs('retrieval', level='ERROR'):
            ids, _, diag = select_evidence(self.engine, 'muestra', [3, 2, 0, 0], [], 2, True)
        self.assertEqual(ids, ['0', '1'])
        self.assertFalse(diag['laya_used'])

    def test_laya_invalid_probabilities_are_rejected(self):
        model = MagicMock()
        model.tok.encode.return_value = [1, 2]
        model.predict_batch.return_value = [{'answers': {'relevance': {
            'choice': 'directa', 'probabilities': {'directa': float('nan'),
             'contexto': 0, 'dudosa': 0, 'irrelevante': 0}}}}]
        with patch('retrieval.laya_model', return_value=model):
            with self.assertRaises(ValueError):
                laya_rank('pregunta', self.engine.rows[:1])

    def test_engine_preserves_citations_text_and_relations(self):
        engine = Engine()
        row = engine.rows[0]
        with patch('retrieval.select_evidence', return_value=(
            [row['chunk_id']], {row['chunk_id']: {'relevance': 'directa'}}, {'laya_used': True})):
            result = engine.search('cocaína', 'laya')
        self.assertEqual(result['sources'][0]['text'], row['text'])
        self.assertEqual(result['sources'][0]['locator'], row['locator'])
        self.assertEqual(result['sources'][0]['citation'], 'F1')
        self.assertTrue(all(e['chunk_id'] == row['chunk_id'] for e in result['relations']))

    def test_semantic_index_handles_long_chunks_and_document_deletion(self):
        import numpy as np
        import retrieval
        model = MagicMock()
        model.tokenizer.encode.side_effect = lambda text, **kw: list(range(len(text)))
        model.tokenizer.decode.side_effect = lambda ids: 'ventana ' + str(ids[-1])
        model.encode.side_effect = lambda texts, **kw: np.asarray([[1., 0.]] * len(texts))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'semantic').mkdir()
            (root / 'semantic' / 'config.json').write_text('{}')
            (root / 'semantic' / 'model.safetensors').write_bytes(b'test')
            with patch('retrieval.MODEL_DIR', root), patch('retrieval.semantic_model', return_value=model), \
                 patch.object(retrieval, '_indexes', __import__('collections').OrderedDict()):
                rows = [{'chunk_id': 'kept', 'text': 'x' * 720},
                        {'chunk_id': 'deleted', 'text': 'breve'}]
                semantic_search('pregunta', rows)
                indexed = model.encode.call_args_list[0].args[0]
                self.assertIn('passage: ventana 719', indexed)
                retrieval._indexes.clear()  # simulate an application restart
                model.encode.reset_mock()
                semantic_search('pregunta', rows)
                self.assertEqual(model.encode.call_count, 1)  # cached passages, only query encoded
                remaining = semantic_search('pregunta', rows[:1])
                self.assertEqual([cid for cid, _ in remaining], ['kept'])

    def test_generation_rejects_declared_but_unused_citation(self):
        result = Engine().search('cocaína')
        fake = MagicMock()
        fake.__enter__.return_value = fake
        fake.chat.completions.create.return_value = SimpleNamespace(choices=[
            SimpleNamespace(message=SimpleNamespace(content=json.dumps(
                {'answer': 'Afirmación [F1]', 'cited_ids': ['F1', 'F2']})))], usage=None)
        with patch('engine.model_config', return_value={'configured': True, 'key': 'test',
                   'base_url': 'http://localhost', 'model': 'test'}), \
             patch('openai.OpenAI', return_value=fake):
            with self.assertRaises(ValueError):
                generate(result)


if __name__ == '__main__':
    unittest.main()
