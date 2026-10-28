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

La actualización quedó verificada para desarrollo con CPU.
