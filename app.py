"""Local-only pilot server. Start with Python app.py; optional model use is per request."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import argparse, json, secrets, threading, webbrowser
from engine import Engine, generate, model_config
from documents import Documents

ROOT=Path(__file__).resolve().parent

def serve(port=8767, open_browser=False):
    documents=Documents();engine=Engine();token=secrets.token_urlsafe(24);busy=threading.BoundedSemaphore(2)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,status,data,ctype='application/json'):
            body=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode()
            self.send_response(status);self.send_header('Content-Type',ctype+'; charset=utf-8')
            self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if self.headers.get('Host') not in {f'127.0.0.1:{port}',f'localhost:{port}'}:return self.send(403,{'error':'Host inválido'})
            if self.path=='/':
                html=(ROOT/'index.html').read_text(encoding='utf8').replace('__TOKEN__',token)
                return self.send(200,html.encode(),'text/html')
            if self.path=='/api/documents':return self.send(200,documents.listing())
            if self.path=='/api/stats':
                with documents.lock:return self.send(200,Engine().stats())
            if self.path=='/api/config':return self.send(200,model_config(public=True))
            if self.path=='/obsidian.zip':
                import io, zipfile
                buffer=io.BytesIO()
                with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
                    for file in (ROOT/'boveda-obsidian').rglob('*'):
                        if file.is_file() and file.suffix in ('.md','.canvas'):
                            archive.write(file,'INTCF/'+file.relative_to(ROOT/'boveda-obsidian').as_posix())
                return self.send(200,buffer.getvalue(),'application/zip')
            if self.path=='/graph':
                graph=ROOT/'graphify-out/graph.html'
                if not graph.is_file():return self.send(404,b'El grafo no esta exportado todavia.','text/plain')
                return self.send(200,graph.read_bytes(),'text/html')
            if self.path=='/health':return self.send(200,{'status':'ok'})
            return self.send(404,{'error':'No encontrado'})
        def do_POST(self):
            if self.path not in ('/api/query','/api/documents/upload','/api/documents/graph'):return self.send(404,{'error':'No encontrado'})
            if self.headers.get('X-Local-Token')!=token:return self.send(403,{'error':'Abre la aplicación local para consultar.'})
            origin=self.headers.get('Origin')
            if origin and origin not in {f'http://127.0.0.1:{port}',f'http://localhost:{port}'}:return self.send(403,{'error':'Origen inválido'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=(22*1024*1024 if self.path=='/api/documents/upload' else 16000):raise ValueError('Petición demasiado grande')
                request=json.loads(self.rfile.read(length))
                if self.path=='/api/documents/upload':return self.send(200,documents.upload(request.get('name'),request.get('content')))
                if self.path=='/api/documents/graph':return self.send(202,documents.start(request.get('document_id')))
                q=request.get('question');mode=request.get('mode','graph')
                if not isinstance(q,str) or not 3<=len(q.strip())<=1200:raise ValueError('Escribe una pregunta de 3 a 1200 caracteres.')
                if mode not in ['graph','baseline']:raise ValueError('Modo no válido')
                if not busy.acquire(blocking=False):return self.send(429,{'error':'Hay dos consultas en curso. Espera un momento.'})
                try:
                    with documents.lock:result=Engine().search(q,mode)
                    if request.get('generate') is True:
                        try:result=generate(result)
                        except ValueError as exc:result['generation_error']=str(exc)
                    self.send(200,result)
                finally:busy.release()
            except (ValueError,TypeError,json.JSONDecodeError) as exc:self.send(400,{'error':str(exc)})
            except Exception:self.send(502,{'error':'No se pudo completar la consulta o conectar con el modelo. Prueba sin redacción externa.'})
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'INTCF GraphRAG: http://127.0.0.1:{port}',flush=True)
    if open_browser:webbrowser.open(f'http://127.0.0.1:{port}')
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8767);p.add_argument('--open',action='store_true');a=p.parse_args();serve(a.port,a.open)
