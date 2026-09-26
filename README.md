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

La redacción de respuestas se hace con un proveedor externo. El piloto opcional descrito abajo añade modelos locales de recuperación y selección. No se ha medido todavía el consumo máximo de RAM en un VPS. La generación de vistas puede consumir más que las consultas. Esta copia no despliega un servicio público ni configura acceso remoto, autenticación o HTTPS. El modo actual escucha solo en la interfaz local.

## Piloto de búsqueda semántica y LAYA

La interfaz permite comparar cuatro métodos: BM25, documentos + grafo original,
búsqueda ampliada y búsqueda ampliada + LAYA. Los modos originales se conservan.
Los modelos opcionales seleccionan evidencia local; la redacción sigue usando el
proveedor configurado únicamente cuando se marca la casilla correspondiente.

Preparación (una vez, con acceso a Internet):

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-retrieval.txt
.venv\Scripts\python.exe prepare_retrieval.py
```

Después abre `ABRIR.cmd` o reinicia el servidor que estuviera abierto. Selecciona
«Búsqueda ampliada + LAYA · piloto» y consulta. «Comparar métodos» muestra los
pasajes de los cuatro métodos sin llamadas al proveedor de redacción.

La búsqueda ampliada combina hasta 30 candidatos mediante BM25, ventanas semánticas
de multilingual-e5-small y relaciones documentadas. No reserva la mitad de los
seis resultados al grafo. LAYA multilingüe valora cada pareja pregunta–fragmento
y ordena esos candidatos. Conserva texto, localizador y documento originales.
En el presupuesto habitual de seis fragmentos se protegen los dos primeros de
BM25 y LAYA selecciona el resto. Esta protección se añadió tras observar una
regresión en la pregunta semilla sobre inmunoensayos: el modelo relegó el pasaje
de referencia a la posición 20. Es un ajuste de desarrollo, no una mejora
demostrada con preguntas independientes. El modo original sigue seleccionado
por defecto; LAYA permanece como piloto explícito.
Sus etiquetas son estimaciones de relevancia, no verificaciones de verdad.
No se aplica todavía un descarte automático basado en la confianza de LAYA.
Si no hay ningún término del corpus ni entidad del grafo reconocidos, los modos
nuevos se abstienen antes de consultar los modelos. Esta protección evita una
regresión observada con palabras inventadas, pero puede omitir preguntas válidas
formuladas sin ningún vocabulario compartido. Tampoco detecta todas las consultas
ajenas al dominio: una pregunta sobre trenes que mencione Madrid puede recuperar
documentos que contienen esa ciudad. Recuperar texto no equivale a poder responder.

Los modelos se guardan en `data/models` y el índice semántico en
`data/retrieval-cache`. Los cambios de contenido invalidan el índice. Las consultas
no descargan modelos ni envían textos a estos servicios: si falta un modelo o
falla, se utiliza la alternativa disponible y se muestra un aviso. La primera
indexación puede tardar varios minutos; los reinicios reutilizan el índice.
Los índices antiguos pueden conservar texto representado como vectores; deben
tratarse como parte de los datos privados y gestionarse con sus mismas políticas.
Los modelos, cachés y resultados de evaluación no se incluyen en Git ni en Docker.
El Dockerfile ligero sigue sin instalar los extras: requiere preparación aparte
para ejecutar modelos locales. No se ha desplegado este piloto en el VPS.

El umbral de similitud semántica de 0,78 y los pesos de combinación son valores
iniciales, sin calibración experta. No deben interpretarse como probabilidades.
El prompt exige responder al aspecto solicitado y señalar carencias de evidencia;
la validación automática de citas comprueba IDs, no respaldo semántico de cada
afirmación. Esa verificación continúa pendiente de una fase posterior.

### Cobertura de preguntas con varios apartados

Al marcar redacción externa, se hace una llamada adicional al proveedor configurado
con la pregunta (sin documentos) para formular hasta tres búsquedas independientes.
Se buscan pasajes por palabras y similitud, conservando los seis originales y
añadiendo hasta cuatro por apartado, con un límite total de 18. La redacción recibe
estos pasajes y sus citas. La interfaz informa del envío ampliado. Sin marcar la
casilla no se utiliza el planificador externo y se mantiene la búsqueda local.

Esta ampliación corrige un caso observado en el que una consulta sobre recogida,
técnicas y consecuencias penales recuperaba un fragmento general de un libro,
pero no su información analítica. Una referencia F5 identifica un **fragmento**,
no todo el libro. El prompt prohíbe inferir que un documento no contiene información
solo porque no aparece en los pasajes recuperados. También distingue métodos para
muestras biológicas de pruebas de sustancias incautadas.

Pruebas adicionales: `python -m unittest test_evidence_coverage -q`.
La recuperación por apartados se ha verificado localmente en el caso observado;
la reproducción con Gemini, autorizada por el usuario, también ha pasado: la respuesta incorpora las técnicas con citas a los fragmentos recuperados. Se verificó este caso concreto; no implica validación general del contenido médico o jurídico.

### Evaluación reproducible

`evaluation/questions.jsonl` contiene 30 preguntas semilla. Solo algunas tienen
pasajes de referencia revisados durante la implementación; las demás esperan
etiquetado experto y ejemplos reales del usuario. No constituyen validación clínica.

```powershell
.venv\Scripts\python.exe evaluate_retrieval.py --limit 4
.venv\Scripts\python.exe -m unittest test_pilot test_documents test_retrieval -q
```

El comparador registra fuentes, tiempos, uso real de los modelos y avisos.
Calcula recuperación de los pasajes etiquetados y posición del primer acierto solo
cuando hay etiquetas. Rechaza IDs que ya no existen en el corpus. No mide calidad
de respuestas generadas, ni convierte casos sin etiquetas en aciertos. El primer
uso incluye tiempo de carga, por lo que no es comparable con tiempos en caliente.
