import base64, shutil, tempfile, unittest
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
    def test_path_and_invalid_content_rejected(self):
        for name,content in [('../escape.txt','YQ=='),('a.txt','?'),('a.exe','YQ=='),('empty.txt','')]:
            with self.assertRaises(ValueError):self.docs.upload(name,content)

if __name__=='__main__':unittest.main()
