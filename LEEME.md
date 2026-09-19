# Piloto INTCF GraphRAG

Abre `ABRIR.cmd` y visita http://127.0.0.1:8767. Mantén abierta la consola del servidor. Si ya hay una instancia en ese puerto, usa el navegador existente. Para detenerla, Ctrl+C en su consola.

## Primera prueba

1. Pulsa «Cocaína + etanol» para recuperar evidencia.
2. Pulsa «Comparar ambos» para ver qué fragmentos cambia el grafo frente a BM25, con seis resultados por método.
3. Abre un fragmento y contrasta las relaciones con sus citas.
4. Abre `.env` en VS Code. Pega tu clave en `GEMINI_API_KEY=` y guarda. El modelo se selecciona con `LLM_MODEL` (por defecto `gemini-3.8-flash`, configurable según acceso de tu cuenta).
5. Marca «Redactar con…» y consulta. Solo se envían la pregunta y hasta seis fragmentos a Gemini. La configuración se recarga en cada consulta.
6. Pulsa «Ver grafo» para explorar el mapa dentro de la web. «Descargar bóveda para Obsidian» descarga un ZIP: descomprímelo, abre la carpeta INTCF como bóveda y abre `INICIO.md`, la vista de grafo o `Mapa-INTCF.canvas`.

La llamada anterior a OpenAI devolvió 429 por saldo agotado. Gemini está integrado, pero la prueba real requiere tu clave. Los errores del proveedor se muestran sin perder las evidencias locales.

## Preparación para GitHub

`.env` es privado y `.env.example` es la plantilla sin claves. `.gitignore` excluye claves, corpus, grafos y bóveda, que contienen textos de los documentos. Todavía no se ha publicado nada.
Para una instalación nueva: crea un entorno con `python -m venv .venv`, instala `requirements.txt` y copia `.env.example` a `.env`. Los datos del piloto se deben aportar por separado en `data/`; clonar solo el código no incluye el corpus. Ejecuta `.venv\Scripts\python app.py --open`.
Si no hay corpus (no existe `data/manifest.json`), la aplicación arranca vacía, con las cifras a cero: sube el primer documento desde «Documentos» y se crean `data/` y el manifiesto. Con `RAG_READONLY=1` no aplica y la ausencia de corpus sigue siendo un error.


## Alcance real

Origen: `C:\Users\Uned\Documents\rag_intcf\data\informes`. El proyecto original, sus PDF y su Chroma no se han modificado.

- 6 PDF, 498 fragmentos, unas 156.000 palabras.
- AnyDoc convirtió cinco documentos; pypdf recuperó localmente el texto del sexto, sin OCR externo.
- Extracción semántica de 40 fragmentos seleccionados por temas (7–9 % del corpus por número de fragmentos, no una muestra aleatoria).
- 102 conceptos y 98 afirmaciones con citas exactas. «EXTRACTED» indica respaldo textual, no revisión científica.
- Graphify produjo una proyección dirigida de 95 aristas y 22 comunidades. Agrupa algunos pares de extremos; las 98 afirmaciones íntegras están en `data/knowledge.json`.

Es un GraphRAG piloto de recuperación mediante grafo explícito y generación opcional. La búsqueda base es BM25 sobre todo el corpus y la expansión recorre relaciones documentadas incidentes a conceptos de la pregunta. No usa todavía embeddings nuevos, consultas Text2Cypher, Neo4j, recorridos de múltiples saltos ni resúmenes de comunidades. El archivo Graphify es una proyección para análisis, no el almacén que consume el recuperador: este usa `knowledge.json` para conservar todas las evidencias.

El comparador no reproduce el RAG Chroma original. Por tanto, no demuestra una mejora frente a él. Esa comparación requiere activar el mismo modelo de embeddings, alinear corpus/fragmentos y evaluar preguntas con referencias humanas.

## Calidad y límites

Se verifican integridad de citas, localizadores de los 498 fragmentos, presupuesto de recuperación, abstención con vocabulario ausente, y aceptación/rechazo de citas generadas mediante mocks. También se probó el comparador desde el navegador.

Los offsets remiten al texto normalizado, no a una página PDF, salvo el documento convertido por páginas con pypdf. Tablas aplanadas, particiones, negaciones y contenido antiguo requieren revisión. Una palabra compartida puede traer evidencia irrelevante: la abstención semántica necesita una evaluación posterior. Las relaciones pueden incluir afirmaciones discutibles de las fuentes; no tomar su presencia como validación toxicológica.

La redacción externa tiene validación de IDs de cita, que no prueba que cada afirmación esté sustentada. El servicio escucha solo en 127.0.0.1 y utiliza un token de sesión para consultas; no está diseñado para publicarse o compartirse en red. No registra preguntas ni claves.

## Reproducción y siguientes pasos

`data/manifest.json` registra originales y versiones; `data/chunks.jsonl` conserva los textos; `data/semantic-sample.json` enumera el alcance semántico. `graphify-out/` conserva la proyección y el informe.

Para ejecutar comprobaciones: usar el Python del entorno original y `test_pilot.py`. Las pruebas de generación son simuladas y no llaman a servicios externos. El servidor reutiliza ese Python; la redacción opcional requiere `openai` y `python-dotenv`, ya disponibles en el entorno local.

Siguiente fase: elegir preguntas reales y evidencias esperadas, ampliar extracción donde falten relaciones, revisar ontología/alias y comparar con el RAG original. Solo después decidir si Neo4j añade valor operativo.


## Añadir documentos desde la web

En «Documentos», selecciona PDF con texto, TXT/Markdown UTF-8 o DOCX y pulsa «Añadir archivos». Límite: 15 MB por archivo y dos millones de caracteres. Los documentos quedan disponibles en las consultas sin reiniciar. Se rechazan contenidos duplicados y nombres existentes; para conservar una versión nueva, usa otro nombre. No se sustituyen ni borran las fuentes anteriores.

La carga extrae texto localmente (pymupdf4llm para PDF, con tablas convertidas a Markdown, y XML del cuerpo para DOCX); no utiliza OCR. Los PDF con páginas sin texto se rechazan para evitar omisiones. En DOCX, revisa tablas, imágenes y elementos fuera del cuerpo, que no se interpretan visualmente.

«Actualizar grafo» envía los fragmentos pendientes del documento al proveedor de .env. Consume cuota, valida citas literales y guarda el progreso por fragmento. Al terminar regenera el mapa y la bóveda. Si falla o cierras el servidor, vuelve a pulsar el botón para continuar. La búsqueda sigue disponible mientras se extraen relaciones. Un fragmento procesado puede no contener ninguna relación explícita. Las relaciones iniciales del piloto son una muestra, por eso se distinguen del progreso completo.

La exportación necesita graphifyy. En este equipo se usa su entorno ya instalado; en otros equipos instala graphifyy en el entorno del servidor o define GRAPHIFY_PYTHON con la ruta del Python que lo tiene instalado. Los archivos nuevos se guardan dentro de data/ (excluido de Git). Haz copias de esa carpeta para respaldar fuentes y progreso. No edites la bóveda exportada como única copia de tus notas personales: los archivos generados pueden actualizarse al exportar.

## Añadir una temática nueva

El motor (BM25, grafo con citas verificadas, interfaz) es el mismo para cualquier
temática; lo que cambia por instancia es el corpus y unas pocas variables de
entorno. Cada instancia corre en su propio contenedor, con el mismo código y su
propio corpus montado como volumen. Sin ninguna variable definida, una
instancia se comporta exactamente como ragtox hoy.

1. **Prepara el corpus aparte** (o salta este paso y empieza con un corpus vacío,
   subiendo los documentos desde la pestaña «Documentos»). Convierte los documentos de la temática nueva
   con `prepare_corpus.py --source <carpeta origen> --output <carpeta destino>
   --corpus-id <id>`. El destino es una carpeta nueva y vacía (no reutilices
   `./data`); ahí es donde luego apuntará `RAG_DATA_DIR`.
2. **Junta `data/`, `graphify-out/` y `boveda-obsidian/` en una carpeta de
   corpus.** `RAG_DATA_DIR` apunta a esa carpeta, que debe contener los tres
   subdirectorios (igual que hoy los contiene la raíz del proyecto). Súbelos al
   servidor como el volumen propio de esa instancia.
3. **Define las variables de la instancia** (todas opcionales; sin definirlas,
   el texto es el de toxicología). Se leen del entorno o, si no están allí, del
   `.env` del proyecto; el entorno manda:
   - `RAG_DATA_DIR`: ruta del corpus preparado en el paso 2.
   - `RAG_SIGLA`: sigla corta (título de pestaña, nombre del ZIP de Obsidian,
     del mapa `Mapa-<sigla>.canvas` y título de la portada de la bóveda);
     p.ej. `URG`, `CONCURSAL`, `ITRABAJO`.
   - `RAG_KICKER`: rótulo pequeño sobre el titular (por defecto,
     `PILOTO DOCUMENTAL · ` seguido de `RAG_SIGLA`).
   - `RAG_TITULO`: titular de la cabecera.
   - `RAG_SUBTITULO`: párrafo bajo el titular.
   - `RAG_EJEMPLOS`: botones de ejemplo, formato `Etiqueta::Pregunta` separados
     por `|`, p.ej. `Etiqueta uno::¿Pregunta uno?|Etiqueta dos::¿Pregunta dos?`.
   - `RAG_AVISO`: aviso del pie de página.
   - `RAG_ALLOWED_HOSTS` / `RAG_ALLOWED_ORIGINS`: dominio público de esa
     instancia.
   - `RAG_PORT`: si conviven varias instancias en el mismo host, cada una con
     su puerto.
4. **Sigue el patrón de `docker-compose.example.yml`**: mismo `build: .` para
   todas las instancias, cada una con su propio `container_name`, su volumen
   de corpus en `RAG_DATA_DIR` y sus variables de texto. No es un archivo para
   desplegar tal cual: sirve de plantilla para tu `docker-compose.yml` real.

Las variables `RAGTOX_*` (nombres previos a que el motor fuese común) se
siguen leyendo como alias de las `RAG_*` correspondientes, para no romper el
despliegue de ragtox ya en marcha.
