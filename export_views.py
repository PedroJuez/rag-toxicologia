from pathlib import Path
import json, re, os
from graphify.build import build_from_json
from graphify.cluster import cluster
from graphify.export import to_html, to_obsidian, to_canvas

root=Path(os.environ.get('RAG_DATA_DIR') or Path(__file__).resolve().parent).resolve()
out=root/'graphify-out'
extraction=json.loads((out/'extraction.json').read_text(encoding='utf8'))
knowledge=json.loads((root/'data/knowledge.json').read_text(encoding='utf8'))
chunks={c['chunk_id']:c for c in map(json.loads,(root/'data/chunks.jsonl').read_text(encoding='utf8').splitlines())}
G=build_from_json(extraction,root=str(root/'data/normalized'),directed=True)
# The full local corpus can exceed Graphify's conservative HTML default.
# Keep a finite ceiling and preserve an explicit operator override.
os.environ.setdefault('GRAPHIFY_VIZ_NODE_LIMIT','10000')
communities=cluster(G)
labels={i:' · '.join(G.nodes[n].get('label',n) for n in sorted(members,key=lambda n:G.degree(n),reverse=True)[:2]) for i,members in communities.items()}
to_html(G,communities,str(out/'graph.html'),community_labels=labels)
vault=root/'boveda-obsidian'
count=to_obsidian(G,communities,str(vault),community_labels=labels)
notes={}
for p in vault.glob('*.md'):
    text=p.read_text(encoding='utf8')
    # PDF concept labels may span lines. Read the complete heading, not its first line.
    match=re.search(r'^# ([\s\S]+?)\n\n',text,re.M)
    if match:notes[match.group(1)]=p
names={n['id']:n['label'] for n in knowledge['nodes']}
to_canvas(G,communities,str(vault/'Mapa-INTCF.canvas'),community_labels=labels,
          node_filenames={n:notes[G.nodes[n]['label']].stem for n in G.nodes})
for node in knowledge['nodes']:
    p=notes.get(node['label'])
    if not p:continue
    text=p.read_text(encoding='utf8').split('\n## Evidencias del piloto')[0]
    extra=['','## Evidencias del piloto','','Las citas son afirmaciones de los documentos, no validación científica. Se incluyen relaciones entrantes y salientes.','']
    for e in knowledge['edges']:
        if node['id'] not in (e['source'],e['target']):continue
        c=chunks[e['chunk_id']]
        other=e['target'] if node['id']==e['source'] else e['source']
        otherp=notes.get(names[other]);link=f'[[{otherp.stem}|{names[other]}]]' if otherp else names[other]
        extra += [f"### {names[e['source']]} → {names[e['target']]}",f"Relación: {e['relation']} · concepto conectado: {link}",'', '> '+e['evidence_quote'].replace('\n','\n> '),'',f"Fuente: {c['source_file']}",f"Fragmento: `{c['chunk_id']}`",f"Localizador: {json.dumps(c['locator'],ensure_ascii=False)}",'']
    p.write_text(text+'\n'.join(extra),encoding='utf8')
(vault/'INICIO.md').write_text('# INTCF · Grafo documental\n\nAbre la vista de grafo de Obsidian para navegar todas las notas. Abre una nota de concepto para leer sus relaciones y citas. Las notas de comunidad agrupan conceptos conectados.\n\nEl alcance aumenta al incorporar documentos. Consulta la pestaña Documentos de la aplicación para conocer el progreso de extracción. Las notas conservan las afirmaciones con sus evidencias; el mapa agrupa algunos pares.\n\nLos colores/comunidades indican agrupaciones del algoritmo, no categorías toxicológicas validadas.\n',encoding='utf8')
print('HTML:',out/'graph.html')
print('Obsidian:',count,'native notes + INICIO; evidence added to',len(notes),'notes')
