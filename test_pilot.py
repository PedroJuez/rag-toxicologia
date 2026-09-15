import json, unittest, re, urllib.request, urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from engine import Engine, generate, ROOT

class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.e=Engine()
    def test_exact_evidence(self):
        for e in self.e.graph['edges']:
            self.assertIn(e['evidence_quote'],self.e.byid[e['chunk_id']]['text'])
            self.assertIn(e['source'],self.e.nodes);self.assertIn(e['target'],self.e.nodes)
    def test_offsets(self):
        cache={}
        for r in self.e.rows:
            path=r['normalized_file']
            if path not in cache:cache[path]=(ROOT/'data'/path).read_text(encoding='utf8')
            loc=r['locator'];self.assertEqual(r['text'],cache[path][loc['start']:loc['end']])
    def test_baseline_graph_budget(self):
        q='¿Qué relación hay entre cocaína, etanol y cocaetileno?'
        a=self.e.search(q,'baseline');b=self.e.search(q,'graph')
        self.assertEqual(len(a['sources']),6);self.assertEqual(len(b['sources']),6)
        self.assertTrue(b['relations']);self.assertTrue(b['new_vs_baseline'])
        self.assertFalse(a['relations'])
    def test_absent_vocabulary_abstains(self):
        self.assertEqual(self.e.search('xyznonexistent abcunknown')['sources'],[])
    def test_generation_rejects_fake_citation(self):
        fake=MagicMock();fake.__enter__.return_value=fake;fake.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({'answer':'Dato [F999]','cited_ids':['F999']})))],usage=None)
        with patch('dotenv.dotenv_values',return_value={'LLM_PROVIDER':'openai','OPENAI_API_KEY':'test-only','LLM_MODEL':'gpt-4o-mini'}),patch('openai.OpenAI',return_value=fake):
            with self.assertRaises(ValueError):generate(self.e.search('cocaína etanol'))
    def test_generation_valid_citation(self):
        fake=MagicMock();fake.__enter__.return_value=fake;fake.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({'answer':'Evidencia de prueba [F1]','cited_ids':['F1']})))],usage=None)
        with patch('dotenv.dotenv_values',return_value={'LLM_PROVIDER':'openai','OPENAI_API_KEY':'test-only','LLM_MODEL':'gpt-4o-mini'}),patch('openai.OpenAI',return_value=fake):
            self.assertEqual(generate(self.e.search('cocaína'))['cited_ids'],['F1'])

if __name__=='__main__':unittest.main()
