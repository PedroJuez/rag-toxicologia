"""Verify the production read-only contract through the real HTTP server."""
import json
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path


class ReadOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        cls.base = f'http://127.0.0.1:{port}'
        cls.process = subprocess.Popen(
            [sys.executable, 'app.py', '--port', str(port)],
            cwd=Path(__file__).resolve().parent,
            env={**os.environ, 'RAG_READONLY': '1', 'RAG_BIND': '127.0.0.1'},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.addClassCleanup(cls.stop)
        for _ in range(100):
            try:
                with urllib.request.urlopen(cls.base + '/health', timeout=1) as response:
                    if response.status == 200:
                        return
            except (OSError, urllib.error.URLError):
                time.sleep(.1)
        raise RuntimeError('Read-only test server did not start')

    @classmethod
    def stop(cls):
        cls.process.terminate()
        cls.process.wait(timeout=10)

    def test_documents_hidden_before_javascript_and_not_in_navigation(self):
        with urllib.request.urlopen(self.base) as response:
            html = response.read().decode('utf8')
        self.assertIn('id="tab-documents" hidden', html)
        self.assertIn("const views=['query','graph'];", html)
        self.assertNotIn("const views=['query','graph','documents'];", html)

    def test_document_endpoints_refuse_access(self):
        for path in ['/api/documents', '/api/documents/upload',
                     '/api/documents/delete', '/api/documents/graph']:
            with self.subTest(path=path):
                request = urllib.request.Request(self.base + path,
                    data=None if path == '/api/documents' else b'{}')
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request)
                self.assertEqual(caught.exception.code, 403)

    def test_provider_config_does_not_expose_credentials(self):
        with urllib.request.urlopen(self.base + '/api/config') as response:
            config = json.load(response)
        self.assertTrue(config['readonly'])
        self.assertNotIn('key', config)
        self.assertNotIn('base_url', config)


if __name__ == '__main__':
    unittest.main()
