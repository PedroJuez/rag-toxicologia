"""Restore the bundled corpus only into a fresh checkout."""
from pathlib import Path
import zipfile, hashlib, json

root=Path(__file__).resolve().parent
archive=root/'corpus-toxicologia.zip'
expected=json.loads((root/'copia.json').read_text(encoding='utf8'))['archive_sha256']
if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:
    raise SystemExit('La copia no coincide con su huella de integridad.')
for name in ('data','graphify-out','boveda-obsidian'):
    if (root/name).exists():raise SystemExit('Ya existe '+name+'. No se sobrescribe el corpus local.')
with zipfile.ZipFile(archive) as z:
    for entry in z.infolist():
        path=(root/entry.filename).resolve()
        if root not in path.parents or entry.filename.split('/')[0] not in ('data','graphify-out','boveda-obsidian'):
            raise SystemExit('Ruta no permitida en la copia.')
    z.extractall(root)
print('Corpus, mapa y bóveda restaurados. Configura .env para usar el proveedor de IA.')
