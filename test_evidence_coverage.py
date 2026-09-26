import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from evidence_coverage import add_evidence, complete_evidence
from engine import Engine, generate


class CoverageTests(unittest.TestCase):
    def test_generation_can_cite_newly_retrieved_evidence(self):
        initial = {'question': '¿Qué técnica se utiliza?',
                   'sources': [{'chunk_id': 'old', 'citation': 'F1', 'text': 'muestras',
                                'source_file': 'libro'}]}
        expanded = dict(initial, sources=initial['sources'] + [
            {'chunk_id': 'new', 'citation': 'F2', 'text': 'técnica documentada', 'source_file': 'libro'}])
        client = MagicMock()
        client.__enter__.return_value = client
        client.chat.completions.create.return_value = SimpleNamespace(choices=[
            SimpleNamespace(message=SimpleNamespace(content=json.dumps({
                'answer': 'La técnica está descrita [F2].', 'cited_ids': ['F2']})))], usage=None)
        with patch('evidence_coverage.complete_evidence', return_value=expanded), \
             patch('engine.model_config', return_value={'model': 'test', 'configured': True,
                   'key': 'test', 'base_url': 'http://localhost'}), \
             patch('openai.OpenAI', return_value=client):
            result = generate(initial, engine=MagicMock())
        self.assertEqual(result['cited_ids'], ['F2'])
        payload = json.loads(client.chat.completions.create.call_args.kwargs['messages'][-1]['content'])
        self.assertEqual(payload['evidence'][1]['text'], 'técnica documentada')
        # Gemini's compatibility endpoint did not preserve the format instruction
        # when it was followed by a second system message in the live regression.
        systems = [m for m in client.chat.completions.create.call_args.kwargs['messages']
                   if m['role'] == 'system']
        self.assertEqual(len(systems), 1)
        self.assertIn('cited_ids', systems[0]['content'])

    def test_original_citations_preserved_and_each_facet_gets_evidence(self):
        original = {'question': 'muestras, técnicas y penas',
                    'sources': [dict(chunk_id='original', citation='F1', text='original',
                                     source_file='libro', locator={'start': 0})]}
        engine = MagicMock()
        engine.byid = {}
        def search(query, mode, k):
            return {'sources': [dict(chunk_id=f'{query}-{i}', text='pasaje',
                                    source_file='libro', locator={'start': i}) for i in range(6)]}
        engine.search.side_effect = search
        with patch('retrieval.semantic_search', return_value=[]):
            result = add_evidence(original, engine, ['muestras', 'técnicas', 'penas'])
        self.assertEqual(result['sources'][0], original['sources'][0])
        self.assertEqual(len(result['sources']), 13)
        self.assertEqual(len(original['sources']), 1)
        self.assertTrue(all(len(q['added_ids']) == 4 for q in result['coverage_searches']))
        self.assertEqual([s['citation'] for s in result['sources']],
                         [f'F{i+1}' for i in range(13)])

    def test_rejects_malformed_planner_without_searching(self):
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(choices=[
            SimpleNamespace(message=SimpleNamespace(content='{"search_queries":"bad"}'))])
        engine = MagicMock()
        result = complete_evidence({'question': 'una pregunta', 'sources': []}, engine, client, 'test')
        self.assertIn('coverage_warning', result)
        engine.search.assert_not_called()
        sent = client.chat.completions.create.call_args.kwargs['messages'][-1]['content']
        self.assertEqual(sent, 'una pregunta')

    def test_new_evidence_is_bounded_and_deduplicated(self):
        rows = [dict(chunk_id=str(i), citation=f'F{i+1}', text='x', source_file='doc') for i in range(30)]
        engine = MagicMock(byid={r['chunk_id']: r for r in rows})
        engine.search.side_effect = [{'sources': rows[6:12]}, {'sources': rows[12:18]},
                                    {'sources': rows[18:24]}]
        with patch('retrieval.semantic_search', return_value=[]):
            result = add_evidence({'sources': rows[:6]}, engine, ['a', 'b', 'c'])
        self.assertEqual(len(result['sources']), 18)
        self.assertEqual(len({r['chunk_id'] for r in result['sources']}), 18)

    def test_user_case_recovers_technical_passage_without_external_calls(self):
        engine = Engine()
        original_id = 'a686acfc27f62be5812379e15d899e6df12991dadf66253e2fe85c402902c442'
        techniques_id = 'a94d868ac04e6d03d53cc2fbce8ff49d232f5e29a7f8c8abcb1f94b23972076d'
        original = {'question': '¿Cómo recoger la muestra y qué técnica usar para cocaína?',
                    'sources': [dict(engine.byid[original_id], citation='F1')]}
        # Recorded semantic candidate from the local reproduction, not an LLM answer.
        with patch('retrieval.semantic_search', return_value=[(techniques_id, .898)]):
            result = add_evidence(original, engine,
                                  ['Técnicas de laboratorio para detectar y confirmar cocaína en muestras del conductor'])
        added = next(s for s in result['sources'] if s['chunk_id'] == techniques_id)
        self.assertEqual(added['text'], engine.byid[techniques_id]['text'])
        self.assertEqual(added['locator'], engine.byid[techniques_id]['locator'])
        self.assertNotEqual(added['citation'], 'F1')


if __name__ == '__main__':
    unittest.main()
