"""Restore the bundled corpus only into a fresh checkout."""
from pathlib import Path
import os, zipfile, hashlib, json

code_root=Path(__file__).resolve().parent
# El zip y su huella van con el código; el destino de la extracción es el
# corpus (RAG_DATA_DIR si está definida, la carpeta del código si no).
data_root=Path(os.environ.get('RAG_DATA_DIR') or code_root).resolve()
archive=code_root/'corpus-toxicologia.zip'
expected=json.loads((code_root/'copia.json').read_text(encoding='utf8'))['archive_sha256']
if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:
    raise SystemExit('La copia no coincide con su huella de integridad.')
data_root.mkdir(parents=True,exist_ok=True)
for name in ('data','graphify-out','boveda-obsidian'):
    if (data_root/name).exists():raise SystemExit('Ya existe '+name+'. No se sobrescribe el corpus local.')
with zipfile.ZipFile(archive) as z:
    for entry in z.infolist():
        path=(data_root/entry.filename).resolve()
        if data_root not in path.parents or entry.filename.split('/')[0] not in ('data','graphify-out','boveda-obsidian'):
            raise SystemExit('Ruta no permitida en la copia.')
    z.extractall(data_root)
print('Corpus, mapa y bóveda restaurados en '+str(data_root)+'. Configura .env para usar el proveedor de IA.')
