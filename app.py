"""Servidor del piloto. En local funciona igual que antes: python app.py

El motor (BM25, grafo, interfaz) es agnóstico del dominio; cada despliegue lo
personaliza con variables de entorno, sin tocar el código. Para desplegarlo
detrás de un proxy inverso también se configura por variables de entorno. Sin
ninguna de ellas, el comportamiento es idéntico al original: escucha solo en
127.0.0.1, rechaza cualquier Host que no sea local y muestra los textos de
toxicología de siempre.

    RAG_BIND             dirección de escucha (por defecto 127.0.0.1; en Docker 0.0.0.0)
    RAG_PORT             puerto (por defecto 8767)
    RAG_ALLOWED_HOSTS    hosts permitidos, separados por comas
                         ej. ragtox.pedrojuezmartel.com
    RAG_ALLOWED_ORIGINS  orígenes permitidos en POST, separados por comas
                         ej. https://ragtox.pedrojuezmartel.com
    RAG_READONLY         1 = sin subida, borrado ni extracción de grafo de documentos
    RAG_DATA_DIR         ruta del corpus (data/, graphify-out/, boveda-obsidian/);
                         por defecto, junto al código, como siempre
    RAG_SIGLA            sigla corta de la instancia (título de pestaña, bóveda
                         de Obsidian); por defecto INTCF
    RAG_TITULO           titular de la cabecera
    RAG_SUBTITULO        párrafo bajo el titular
    RAG_EJEMPLOS         botones de ejemplo: "Etiqueta::Pregunta" separados por |
    RAG_AVISO            aviso del pie de página

    Las variables RAGTOX_* (nombres anteriores a que el motor fuese común a
    varios RAG) se siguen leyendo si RAG_* no está definida, para no romper el
    despliegue ya en marcha de ragtox.

Por qué el modo de solo lectura: /api/documents/graph llama al proveedor con tu
clave. Publicado sin autenticación, cualquiera podría consumir la cuota, subir
contenido o borrar el corpus. Con RAG_READONLY=1 esos extremos devuelven 403
y la pestaña «Documentos» se oculta en la interfaz. El corpus se prepara en
local y se despliega ya hecho.
"""

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import argparse, json, os, secrets, threading, webbrowser

from engine import Engine, generate, model_config, DATA_DIR
from documents import Documents

ROOT = Path(__file__).resolve().parent


def _env(nombre, default=''):
    """RAG_<nombre>, o RAGTOX_<nombre> por compatibilidad, o el valor por defecto."""
    return os.environ.get('RAG_' + nombre) or os.environ.get('RAGTOX_' + nombre) or default


def _lista(nombre):
    return {x.strip() for x in (_env(nombre) or '').split(',') if x.strip()}


def _esc_html(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _esc_attr(s):
    return _esc_html(s).replace('"', '&quot;')


READONLY = _env('READONLY').strip() in ('1', 'true', 'yes')


def serve(port=8767, open_browser=False, bind=None):
    bind = bind or _env('BIND', '127.0.0.1')
    documents = Documents()
    token = secrets.token_urlsafe(24)
    busy = threading.BoundedSemaphore(2)

    hosts_ok = _lista('ALLOWED_HOSTS') | {f'127.0.0.1:{port}', f'localhost:{port}'}
    origins_ok = _lista('ALLOWED_ORIGINS') | {f'http://127.0.0.1:{port}',
                                              f'http://localhost:{port}'}

    # Con el corpus fijo, el índice BM25 no cambia: se construye una sola vez.
    # Sin RAG_READONLY se mantiene el comportamiento original (un motor nuevo
    # por consulta), que es lo que permite ver los documentos recién subidos.
    _cache = {}

    def motor():
        if not READONLY:
            return Engine()
        if 'engine' not in _cache:
            _cache['engine'] = Engine()
        return _cache['engine']

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def send(self, status, data, ctype='application/json'):
            body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status); self.send_header('Content-Type', ctype + '; charset=utf-8')
            self.send_header('Content-Length', str(len(body))); self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff'); self.end_headers(); self.wfile.write(body)

        def host_valido(self):
            host = (self.headers.get('Host') or '').split(',')[0].strip()
            return host in hosts_ok or host.split(':')[0] in {h.split(':')[0] for h in hosts_ok}

        def do_GET(self):
            if not self.host_valido():
                return self.send(403, {'error': 'Host inválido'})
            if self.path == '/':
                sigla = _env('SIGLA', 'INTCF')
                titulo = _env('TITULO', 'De encontrar textos a conectar evidencias')
                subtitulo = _env('SUBTITULO', 'Explora tus documentos, consulta sus fragmentos y '
                                  'comprueba qué relaciones añade el grafo. Una prueba local para '
                                  'evaluar el método, con las fuentes siempre a la vista.')
                aviso = _env('AVISO', 'Uso exploratorio y documental. No validado para conclusiones '
                             'periciales. El comparador utiliza una base BM25 local; no mide el RAG '
                             'semántico Chroma original.')
                ejemplos_raw = _env('EJEMPLOS',
                    'Cocaína + etanol::¿Qué relación hay entre cocaína, etanol y cocaetileno?|'
                    'Metabolitos y muestras::¿Qué metabolitos de cocaína se detectan en orina?|'
                    'Cribado y confirmación::¿Qué limitaciones tienen los inmunoensayos para detectar drogas?|'
                    'EtG y cabello::¿Cómo se relaciona el etilglucurónido con el consumo de etanol y el cabello?')
                ejemplos = [tuple(p.split('::', 1)) for p in ejemplos_raw.split('|') if '::' in p]
                ejemplos_html = ''.join(
                    f'<button data-q="{_esc_attr(pregunta.strip())}">{_esc_html(etiqueta.strip())}</button>'
                    for etiqueta, pregunta in ejemplos)
                pregunta_inicial = ejemplos[0][1].strip() if ejemplos else ''
                html = (ROOT / 'index.html').read_text(encoding='utf8')
                html = (html.replace('__TOKEN__', token)
                            .replace('__SIGLA__', _esc_html(sigla))
                            .replace('__TITULO__', _esc_html(titulo))
                            .replace('__SUBTITULO__', _esc_html(subtitulo))
                            .replace('__AVISO__', _esc_html(aviso))
                            .replace('__EJEMPLOS__', ejemplos_html)
                            .replace('__PREGUNTA_INICIAL__', _esc_html(pregunta_inicial)))
                if READONLY:
                    # Oculta la pestaña de documentos sin tocar index.html
                    html = html.replace(
                        '</script></html>',
                        "\ndocument.getElementById('tab-documents').hidden=true;\n</script></html>")
                return self.send(200, html.encode(), 'text/html')
            if self.path == '/api/documents': return self.send(200, documents.listing())
            if self.path == '/api/stats':
                with documents.lock: return self.send(200, motor().stats())
            if self.path == '/api/config':
                config = model_config(public=True); config['readonly'] = READONLY
                return self.send(200, config)
            if self.path == '/obsidian.zip':
                import io, zipfile
                sigla = _env('SIGLA', 'INTCF')
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
                    for file in (DATA_DIR / 'boveda-obsidian').rglob('*'):
                        if file.is_file() and file.suffix in ('.md', '.canvas'):
                            archive.write(file, sigla + '/' + file.relative_to(DATA_DIR / 'boveda-obsidian').as_posix())
                return self.send(200, buffer.getvalue(), 'application/zip')
            if self.path == '/graph':
                graph = DATA_DIR / 'graphify-out/graph.html'
                if not graph.is_file(): return self.send(404, b'El grafo no esta exportado todavia.', 'text/plain')
                return self.send(200, graph.read_bytes(), 'text/html')
            if self.path == '/health': return self.send(200, {'status': 'ok'})
            return self.send(404, {'error': 'No encontrado'})

        def do_POST(self):
            if not self.host_valido():
                return self.send(403, {'error': 'Host inválido'})
            if self.path not in ('/api/query', '/api/documents/upload', '/api/documents/graph',
                                 '/api/documents/delete'):
                return self.send(404, {'error': 'No encontrado'})
            if READONLY and self.path != '/api/query':
                return self.send(403, {'error': 'Esta instalación es de solo consulta. '
                                                'El corpus se actualiza en local.'})
            if self.headers.get('X-Local-Token') != token:
                return self.send(403, {'error': 'Recarga la página para consultar.'})
            origin = self.headers.get('Origin')
            if origin and origin not in origins_ok:
                return self.send(403, {'error': 'Origen inválido'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= (22 * 1024 * 1024 if self.path == '/api/documents/upload' else 16000):
                    raise ValueError('Petición demasiado grande')
                request = json.loads(self.rfile.read(length))
                if self.path == '/api/documents/upload':
                    return self.send(200, documents.upload(request.get('name'), request.get('content')))
                if self.path == '/api/documents/delete':
                    return self.send(200, documents.delete(request.get('document_id')))
                if self.path == '/api/documents/graph':
                    return self.send(202, documents.start(request.get('document_id')))
                q = request.get('question'); mode = request.get('mode', 'graph')
                if not isinstance(q, str) or not 3 <= len(q.strip()) <= 1200:
                    raise ValueError('Escribe una pregunta de 3 a 1200 caracteres.')
                if mode not in ['graph', 'baseline']: raise ValueError('Modo no válido')
                if not busy.acquire(blocking=False):
                    return self.send(429, {'error': 'Hay dos consultas en curso. Espera un momento.'})
                try:
                    if READONLY:
                        result = motor().search(q, mode)     # índice ya construido
                    else:
                        with documents.lock: result = Engine().search(q, mode)
                    if request.get('generate') is True:
                        try: result = generate(result)
                        except ValueError as exc: result['generation_error'] = str(exc)
                    self.send(200, result)
                finally:
                    busy.release()
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                self.send(400, {'error': str(exc)})
            except Exception:
                self.send(502, {'error': 'No se pudo completar la consulta o conectar con el modelo. '
                                         'Prueba sin redacción externa.'})

    server = ThreadingHTTPServer((bind, port), Handler)
    print(f'{_env("SIGLA", "INTCF")} GraphRAG escuchando en {bind}:{port}'
          + (' · solo consulta' if READONLY else ''), flush=True)
    if open_browser: webbrowser.open(f'http://127.0.0.1:{port}')
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--port', type=int, default=int(_env('PORT', '8767')))
    p.add_argument('--open', action='store_true')
    p.add_argument('--bind', default=None)
    a = p.parse_args()
    serve(a.port, a.open, a.bind)
