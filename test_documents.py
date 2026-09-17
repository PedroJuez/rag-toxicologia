import base64, json, shutil, tempfile, unittest
from pathlib import Path
from engine import Engine, ROOT
from documents import Documents, verified_relations

class DocumentTests(unittest.TestCase):
    def test_whitespace_quote_uses_exact_source(self):
        r=dict(source='Muestra',target='Frío',relation='requiere',evidence_quote='La muestra requiere frío.')
        text='La muestra\n requiere frío.'
        self.assertEqual(verified_relations({'relations':[r]},text)[0]['evidence_quote'],text)
        r['evidence_quote']='La muestra no requiere frío.'
        with self.assertRaises(ValueError):verified_relations({'relations':[r]},text)
    def test_bad_chunk_does_not_stop_following_chunks(self):
        from unittest.mock import patch, MagicMock
        from types import SimpleNamespace
        e=Engine(self.root);docid=e.rows[0]['document_id']
        rows=[c for c in e.rows if c['document_id']==docid][:2]
        e.rows=rows
        client=MagicMock();client.__enter__.return_value=client
        client.chat.completions.create.side_effect=[
            SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"relations":[{"source":"a","target":"b","relation":"r","evidence_quote":"invented quote never in corpus"}]}'))]),
            SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"relations":[]}'))])]
        with patch('documents.Engine',return_value=e),patch.object(self.docs,'progress',return_value=[]),patch('documents.model_config',return_value={'key':'test','base_url':'http://localhost','model':'test'}),patch('openai.OpenAI',return_value=client),patch.object(self.docs,'export') as export:
            client.chat.completions.create.side_effect=[client.chat.completions.create.side_effect.__next__()]*2+[SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"relations":[]}'))])]
            self.docs.extract(docid)
        self.assertEqual(self.docs.status['state'],'partial')
        self.assertEqual(self.docs.progress(),[rows[1]['chunk_id']])
        export.assert_called_once()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        shutil.copytree(ROOT/'data',self.root/'data');self.docs=Documents(self.root)
    def tearDown(self):self.tmp.cleanup()
    def test_upload_retrievable_and_duplicate_rejected(self):
        text='Pruebax pertenece al grupo Ensayoy.'
        data=base64.b64encode(text.encode()).decode()
        self.docs.upload('prueba.txt',data)
        result=Engine(self.root).search('Pruebax')
        self.assertEqual(result['sources'][0]['source_file'],'prueba.txt')
        with self.assertRaises(ValueError):self.docs.upload('otro.txt',data)
    def test_delete_removes_all_traces_and_engine_reloads(self):
        text='Sustanciaz interactua con Receptorw.'
        data=base64.b64encode(text.encode()).decode()
        docid=self.docs.upload('borrable.txt',data)['document_id']
        e=Engine(self.root)
        record=next(d for d in e.manifest['documents'] if d['document_id']==docid)
        chunk_ids={c['chunk_id'] for c in e.rows if c['document_id']==docid}
        normalized_path=self.root/'data'/record['normalized_file']
        upload_path=self.root/'data'/'uploads'/(docid+'.txt')
        self.assertTrue(normalized_path.exists());self.assertTrue(upload_path.exists())
        self.docs.delete(docid)
        manifest=json.loads((self.root/'data/manifest.json').read_text(encoding='utf8'))
        self.assertNotIn(docid,{d['document_id'] for d in manifest['documents']})
        rows=[json.loads(x) for x in (self.root/'data/chunks.jsonl').read_text(encoding='utf8').splitlines()]
        self.assertFalse(any(r['document_id']==docid for r in rows))
        graph=json.loads((self.root/'data/knowledge.json').read_text(encoding='utf8'))
        self.assertFalse(any(x['chunk_id'] in chunk_ids for x in graph['edges']))
        progress=json.loads((self.root/'data/graph-progress.json').read_text(encoding='utf8'))
        self.assertFalse(chunk_ids & set(progress))
        self.assertFalse(normalized_path.exists());self.assertFalse(upload_path.exists())
        Engine(self.root)  # reconstruye el motor y comprueba sus aserciones de integridad
        with self.assertRaises(ValueError):self.docs.delete(docid)
    def test_path_and_invalid_content_rejected(self):
        for name,content in [('../escape.txt','YQ=='),('a.txt','?'),('a.exe','YQ=='),('empty.txt','')]:
            with self.assertRaises(ValueError):self.docs.upload(name,content)

if __name__=='__main__':unittest.main()
