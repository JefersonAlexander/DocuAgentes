# Actualización aplicada para Python 3.12

Fecha: 28 de octubre de 2026.

> Este documento conserva la validación de la migración inicial de bibliotecas.
> La posterior sustitución de Gemini por embeddings locales y su validación
> están descritas en [local-embeddings.md](local-embeddings.md).

Se instaló Python 3.12.16 en `.python/` y se creó `.venv/` con el perfil CPU.
El Python global del equipo se conserva. El proyecto declara `>=3.12,<3.13`
y selecciona esa rama mediante `.python-version`.

## Dependencias y código

- `pyproject.toml` contiene las dependencias directas y los perfiles CPU/CUDA.
- `uv.lock` fija el árbol completo y los orígenes de PyTorch por perfil.
- `requirementsCPU.txt` y `requirementsCuda.txt` se generaron desde el bloqueo
  con hashes y marcadores de plataforma.
- Gradio usa la API de la rama 6 para `theme`, `css` y `js`.
- `EnsembleRetriever` se importa desde `langchain_classic`.
- Pydantic Settings usa `SettingsConfigDict`.
- La carga de archivos admite rutas de Gradio y objetos de archivo anteriores.
- Los ejemplos usan los PDF existentes en la carpeta del proyecto.
- El índice y la caché nuevos usan `chroma_db_v2/` y `document_cache_v2/`.
  Las carpetas anteriores se conservan.
- El modelo Groq sigue siendo `llama-3.1-8b-instant`, temperatura 0.5 y 256 tokens.

Las dependencias raíz sin consumidores en la aplicación dejaron de fijarse
manualmente. Los paquetes que siguen siendo necesarios de forma transitiva se
conservan en el bloqueo. Por ejemplo, Kubernetes sigue siendo requerido por
Chroma, aunque la aplicación no lo importa directamente.

## Evidencia de validación

- Instalación del perfil Windows/CPU: 195 distribuciones.
- `uv pip check`: todas las dependencias instaladas son compatibles.
- `uv lock --check --offline`: bloqueo consistente con el proyecto.
- `uv sync --locked --extra cuda --dry-run --offline`: cambio de los dos
  paquetes PyTorch/torchvision a sus variantes CUDA 13.0 resuelto correctamente.
- 15 pruebas aprobadas sobre Python 3.12.16: ocho pruebas de los agentes y
  siete integraciones con bibliotecas instaladas.
- Integraciones comprobadas: conversión TXT/DOCX/Markdown con Docling,
  deduplicación y caché; archivos como rutas; lectura de `.env` y prioridad de
  entorno; BM25 y Chroma persistente con embeddings deterministas de prueba;
  operaciones nativas PyTorch/torchvision; flujo LangGraph con mensajes de
  LangChain y respuestas Groq simuladas; construcción de la interfaz Gradio.
- Se comprobaron imports de PyTorch, torchvision, Transformers, Docling,
  Gradio, los retrievers y las integraciones de los agentes.

Las pruebas de integración se ejecutaron fuera del sandbox después de que las
restricciones de Windows bloquearan los directorios temporales. Se observaron
avisos de deprecación de langchain-community y de cierre de event loops, sin
fallos de prueba. No se iniciaron servidores públicos ni se consumieron APIs
de Groq/Gemini. No se validó inferencia PDF con descarga de modelos ni ejecución
CUDA en una GPU.

## Auditoría del entorno instalado

La consulta OSV se guardó en
[`dependency-verification-python312.json`](dependency-verification-python312.json).
Dos distribuciones siguen teniendo avisos asociados a sus versiones:

- **Pillow 12.3.0:** Gradio 6.31.0 exige `Pillow<13`. Hay avisos de procesamiento
  de imágenes cuyo parche está en 13.0.0, como
  [GHSA-22hg-r758-rrw9](https://github.com/advisories/GHSA-22hg-r758-rrw9) y
  [GHSA-24rc-8hj2-v98c](https://github.com/advisories/GHSA-24rc-8hj2-v98c).
  Instalar Pillow 13 ignorando dependencias dejaría el entorno fuera de las
  restricciones declaradas por Gradio. La actualización no elimina estos
  avisos: requieren una versión de Gradio que admita el parche o una migración
  adicional de la interfaz/procesamiento.
- **ChromaDB 1.5.9:** los avisos revisados de autorización de servidor no
  publican una versión corregida. Ejemplos:
  [GHSA-2wm9-hf6c-p5cr](https://github.com/advisories/GHSA-2wm9-hf6c-p5cr) y
  [GHSA-xph7-9rjv-w5fr](https://github.com/advisories/GHSA-xph7-9rjv-w5fr).
  Este proyecto usa persistencia local embebida, sin configurar los proveedores
  de autorización de servidor descritos en esos dos avisos. Esto no demuestra
  ausencia de exposición para todos los avisos devueltos por OSV.

La actualización queda verificada para desarrollo con CPU. La compatibilidad
de instalación y las pruebas funcionales no equivalen a una aprobación de
seguridad para producción; los hallazgos anteriores permanecen documentados.
