# Piloto LAYA — 26 de septiembre de 2026

Implementado y ejecutado localmente con 590 fragmentos. No desplegado en el VPS.
Los resultados iniciales **no justifican activar LAYA por defecto**.

## Qué se midió

Se ejecutaron los cuatro métodos sobre cuatro preguntas de desarrollo: dos con
un pasaje de referencia comprobado en el corpus y dos controles negativos. Las
30 preguntas de `questions.jsonl` son un punto de partida, no un conjunto experto
completamente etiquetado. No se evaluó la redacción mediante un proveedor externo.

| Prueba | Resultado observado |
|---|---|
| Limitaciones de inmunoensayos | Sin protección, LAYA relegó el pasaje de referencia de la primera a la posición 20 entre candidatos. |
| Mismo caso, con protección | El pasaje se conserva primero porque se retienen los dos mejores resultados BM25. No prueba una mejora de LAYA. |
| Confirmación de cribado | Los cuatro métodos conservaron el pasaje de referencia entre seis. La búsqueda ampliada lo situó tercero; los demás, primero. |
| Horario de tren Madrid–Sevilla | Todos recuperaron fragmentos ajenos a la intención. La abstención temática sigue pendiente. |
| Palabras inventadas | La búsqueda semántica inicial recuperó fragmentos; la regla final de vocabulario devuelve cero en los cuatro métodos. |

Los ajustes se hicieron a partir de estos casos; sus resultados no representan
una evaluación independiente. La presencia de un pasaje de referencia tampoco
prueba que los otros cinco resultados sean pertinentes ni que la respuesta sea correcta.

## Tiempo observado en este ordenador

- Primera construcción del índice semántico: unos 125 segundos en la prueba registrada.
- Búsqueda ampliada con índice en disco, incluyendo carga inicial: 10,3 segundos.
- Búsqueda ampliada con el modelo cargado: 0,47–0,57 segundos en tres consultas.
- Búsqueda con LAYA: 34–46 segundos en las cuatro consultas antes de la última regla.
- Palabras inventadas con la protección final: aproximadamente 0,4 segundos, sin modelos.

Son mediciones puntuales, no un benchmark de rendimiento ni una garantía para el VPS.

## Estado entregado

- Se mantiene el método original por defecto; LAYA puede seleccionarse en la interfaz.
- Recuperación ampliada con hasta 30 candidatos y seis pasajes finales.
- Los dos primeros pasajes BM25 se conservan en el modo LAYA habitual.
- Modelos locales instalados y probados; índice persistente reutilizable.
- Fallback visible si falta o falla un modelo.
- 22 pruebas automatizadas verificadas (21 en la ejecución conjunta y una prueba
  adicional de caché; las 11 de recuperación se repitieron tras la última regla).
- Comprobación de sintaxis JavaScript y pruebas HTTP de la interfaz y API.

Las observaciones completas están en `results.json`, la comprobación posterior de
la abstención en `results-negative.json` y la prueba inicial sin protección en
`../data/retrieval-smoke.json`. Esos archivos contienen fragmentos privados y no
se versionan. Se pueden regenerar con `evaluate_retrieval.py` sobre el código
actual; los resultados históricos previos a las protecciones serán distintos.

## Siguiente criterio de aceptación

Recoger preguntas que hayan fallado al usuario y etiquetar los pasajes necesarios
y respuestas esperadas. Reservar preguntas independientes de las utilizadas para
ajustar. Antes de cambiar el método por defecto, exigir menos omisiones de evidencia,
menos afirmaciones sin respaldo y una latencia aceptable. Si LAYA no aporta una
ventaja, evaluar un modelo específico de reordenación o especializarlo con ejemplos
del dominio; no asumir que sus etiquetas o confianza certifican relevancia.
