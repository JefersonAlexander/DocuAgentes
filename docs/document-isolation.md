# Respuestas provenientes de una carga anterior

## Causa reproducida

`RetrieverBuilder` utilizaba `Chroma.from_documents` con una colección persistente
identificada solo por el modelo y la fragmentación. Cada carga agregaba vectores a
esa colección compartida. BM25 recibía los fragmentos actuales, pero la búsqueda
vectorial consultaba también los documentos anteriores; el buscador híbrido podía
entregar esas fuentes a los agentes.

La comprobación de hashes de la interfaz detectaba el cambio de archivo y construía
un nuevo buscador, pero ese buscador seguía conectado a la misma colección. No era
un fallo de Docling ni un problema que se resolviera cambiando CPU por GPU.

La prueba de regresión cargó primero `environment.md` y después `passwords.md`.
Antes de la corrección, una consulta al segundo recuperaba también `environment.md`.

## Corrección

- Una colección por conjunto de fragmentos, con una huella SHA-256 de contenido y
  metadatos, además de la configuración del modelo. Cambiar documentos cambia de
  colección. Un buscador ya creado conserva su propio conjunto.
- Identificadores estables por fragmento y escritura únicamente de los que faltan.
  Recargar el mismo conjunto, incluso en otro orden, no vuelve a generar sus
  embeddings ni agrega duplicados.
- La caché de conversión se reutiliza, actualizando siempre nombre y hash del archivo
  activo. Un archivo renombrado conserva la atribución correcta.
- La interfaz limpia respuestas y buscador al cambiar archivos, también mediante
  los ejemplos. Se cancelan consultas pendientes y una revisión de sesión descarta
  resultados en curso que correspondan a la selección anterior.
- Un error al convertir cualquiera de los archivos seleccionados impide consultar
  una selección incompleta o mantener el buscador de una carga anterior.

## Validación y uso

Las pruebas en `test/test_document_isolation.py` comprueban Chroma y BM25 reales con
embeddings deterministas, cambios de archivos en los callbacks de Gradio, cargas
fallidas, resultados obsoletos en curso y atribución al reutilizar la caché. No envían
documentos ni consultas a Groq.

Validación del 28 de octubre de 2026: las 32 pruebas de la suite completa pasaron
con Python 3.12 en el entorno CPU, incluidas las 10 nuevas pruebas de regresión.
El fallo de mezcla de fuentes se reprodujo antes de modificar el buscador.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s test -v
```

Reiniciar el proceso de la aplicación y cargar los archivos deseados. La primera
consulta crea la colección aislada usando el texto ya convertido en caché cuando
está disponible. Las colecciones antiguas se conservan y dejan de consultarse;
no es necesario borrar la base ni descargar nuevamente los modelos. Mantener
muchos conjuntos diferentes aumenta el espacio ocupado por los índices persistentes.
