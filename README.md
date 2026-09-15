# RAG de toxicología · copia privada

Copia del piloto documental INTCF que incluye el código y una instantánea de los ocho documentos procesados: 565 fragmentos. La clave de API no se incluye.

## Restaurar y abrir

1. Descarga o clona el repositorio en una carpeta propia.
2. Ejecuta `python restaurar_corpus.py`. Descomprime el corpus, el mapa y la bóveda sin sobrescribir carpetas existentes y comprueba la huella de la copia.
3. Crea un entorno: `python -m venv .venv`.
4. Instala las dependencias con el Python de ese entorno: `python -m pip install -r requirements.txt`.
5. Copia `.env.example` a `.env` y configura tu proveedor, clave y modelo disponible. Para búsquedas locales no necesitas API.
6. Con el entorno activado, ejecuta `python app.py --open`; en Windows también puedes utilizar `ABRIR.cmd`.

El servidor escucha en `127.0.0.1:8767`. El repositorio es una copia privada del corpus, no una publicación de los documentos para su redistribución. Contiene textos completos convertidos y las fuentes originales que estaban conservadas en `data/uploads`; no incluye todos los PDF originales de las seis fuentes iniciales ni su antigua base Chroma.

## Contenido y conservación

- `corpus-toxicologia.zip`: datos, progreso de extracción, grafo HTML y notas de Obsidian ya generados.
- `copia.json`: fecha, tamaños y huella SHA-256 del archivo.
- Código del piloto, con arranque portátil y dependencia de Graphify declarada.
- `LEEME.md`: notas históricas del piloto; sus cifras iniciales de seis PDF y 40 fragmentos de muestra describen aquella fase, no esta copia completa.

La instantánea no se actualiza automáticamente cuando añades documentos en tu ordenador. Los datos restaurados y `.env` están ignorados por Git. La instantánea ZIP se incluye deliberadamente para permitir recuperar este corpus.

## VPS

Los archivos del proyecto original ocupan unos 34 MB (medición del 15-09-2026). El entorno de dependencias comparable instalado en Windows ocupa unos 151 MB; el tamaño de la instalación Linux puede variar. Reserva orientativamente 0,5–1 GB de disco para esta aplicación y su entorno, aparte del sistema operativo, registros y futuras copias.

No contiene un modelo de lenguaje local: las llamadas se hacen a un proveedor externo. No se ha medido todavía el consumo máximo de RAM en un VPS. La generación de vistas puede consumir más que las consultas. Esta copia no despliega un servicio público ni configura acceso remoto, autenticación o HTTPS. El modo actual escucha solo en la interfaz local.
