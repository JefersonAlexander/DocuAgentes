# Análisis de dependencias de multiagents

Fecha de revisión: 28 de octubre de 2026.

> Diagnóstico previo a la implementación. La actualización a Python 3.12 ya
> tiene sus versiones efectivas en `../pyproject.toml` y `../uv.lock`.
> Consultar `../README.md` para instalación, perfiles y validación actual.

La solución recomendada es una actualización coordinada sobre Python 3.12,
separando las dependencias directas de la aplicación de las dependencias
transitivas y generando un bloqueo reproducible para cada plataforma de destino.
Las versiones que siguen son candidatas verificadas en los metadatos publicados;
todavía no constituyen un entorno instalado y validado de extremo a extremo.

## Alcance y evidencia

- `requirementsCPU.txt`: 222 paquetes fijados.
- `requirementsCuda.txt`: 236 paquetes fijados.
- Paquetes declarados distintos: 236. Se consultaron además `langchain-classic`,
  `groq`, `google-genai` y `uv` como posibles componentes de la actualización.
- Se identificaron 12 módulos externos importados directamente por la aplicación.
  También deben conservarse dependencias que las integraciones cargan en ejecución,
  como `rank-bm25`.
- Solo se encontró Python 3.15 en el lanzador local. No se encontró `uv` ni
  `pip-audit` instalado.
- El inventario de PyPI excluye versiones retiradas y versiones preliminares,
  y toma publicaciones hasta el 28 de octubre de 2026. Cinco paquetes de
  instrumentación OpenTelemetry solo tienen publicaciones beta; se identifican
  como `beta-only`, sin presentarlas como versiones estables.
- Se consultó OSV para las versiones declaradas: 44 paquetes tienen avisos
  asociados. No se auditó un entorno instalado ni se demostró alcanzabilidad de
  cada vulnerabilidad desde el código de DocChat. Los identificadores GHSA/PYSEC
  pueden representar el mismo problema; no deben sumarse como fallos únicos.
- Una comprobación de los requisitos de 17 versiones actuales contra los pins
  declarados, para Windows/Python 3.12 y sin extras, no encontró conflictos.
  Esa comprobación parcial no equivale a resolver todo el árbol.

Archivos de evidencia:

- [Inventario completo CSV](dependency-versions-2026-10-28.csv).
- [Metadatos de versiones y restricciones JSON](dependency-versions-2026-10-28.json).
- [Avisos OSV y detalles seleccionados JSON](dependency-advisories-2026-10-28.json).

## Versiones objetivo y prioridad

P0 significa resolver antes de poner en servicio un entorno actualizado; P1 es
la migración principal; P2 es la renovación de dependencias auxiliares; P3 es
conservar lo que ya está actualizado. El orden no equivale a actualizar cada
paquete por separado: las familias relacionadas se deben resolver juntas.

| Prioridad | Paquete | Versión declarada | Estable publicada | Objetivo propuesto |
|---|---|---|---|---|
| P0 | Python | 3.15 local | No evaluada como paquete PyPI | 3.12, último parche de esa rama disponible al instalar |
| P0 | gradio | 5.13.2 | [6.31.0](https://pypi.org/project/gradio/6.31.0/) | 6.31.0, adaptando la interfaz |
| P0 | langchain-core | 0.3.32 | [1.7.1](https://pypi.org/project/langchain-core/1.7.1/) | 1.7.1, junto con todas las integraciones |
| P0 | langgraph | 0.2.68 | [1.2.18](https://pypi.org/project/langgraph/1.2.18/) | 1.2.18, con checkpoint/SDK resueltos de nuevo |
| P0 | h11 / httpcore | 0.14.0 / 1.0.7 | [0.16.0](https://pypi.org/project/h11/0.16.0/) / [1.0.9](https://pypi.org/project/httpcore/1.0.9/) | Ambas versiones, como resultado del bloqueo HTTP |
| P0 | aiohttp | 3.11.11 | [3.14.5](https://pypi.org/project/aiohttp/3.14.5/) | 3.14.5, resuelto transitivamente |
| P0 | requests / urllib3 | 2.32.3 / 2.1.0 | [2.34.2](https://pypi.org/project/requests/2.34.2/) / [2.8.0](https://pypi.org/project/urllib3/2.8.0/) | Ambas versiones, resueltas transitivamente |
| P1 | langchain | 0.3.16 | [1.4.7](https://pypi.org/project/langchain/1.4.7/) | Reemplazar su uso actual por langchain-classic 1.0.8; añadir langchain 1.4.7 solo si se usan sus APIs |
| P1 | langchain-classic | No declarado | [1.0.8](https://pypi.org/project/langchain-classic/1.0.8/) | 1.0.8 para EnsembleRetriever |
| P1 | langchain-groq | 0.2.3 | [1.1.3](https://pypi.org/project/langchain-groq/1.1.3/) | 1.1.3 |
| P1 | langchain-google-genai | 2.0.9 | [4.4.2](https://pypi.org/project/langchain-google-genai/4.4.2/) | 4.4.2 |
| P1 | langchain-community | 0.3.16 | [0.4.2](https://pypi.org/project/langchain-community/0.4.2/) | 0.4.2 para BM25Retriever |
| P1 | langchain-chroma / chromadb | 0.2.1 / 0.6.3 | [1.1.0](https://pypi.org/project/langchain-chroma/1.1.0/) / [1.5.9](https://pypi.org/project/chromadb/1.5.9/) | Ambas versiones, con copia y prueba del índice |
| P1 | langchain-text-splitters | 0.3.5 | [1.1.3](https://pypi.org/project/langchain-text-splitters/1.1.3/) | 1.1.3 |
| P1 | docling | 2.15.0 | [2.144.0](https://pypi.org/project/docling/2.144.0/) | 2.144.0, resolviendo de nuevo su familia |
| P1 | torch / torchvision | 2.6.0 / 0.21.0, con sufijo CPU en el archivo CPU | [2.14.1](https://pypi.org/project/torch/2.14.1/) / [0.29.1](https://pypi.org/project/torchvision/0.29.1/) | Pareja candidata; validar distribución CPU/CUDA y modelos Docling |
| P1 | transformers | 4.48.1 | [5.21.0](https://pypi.org/project/transformers/5.21.0/) | 5.21.0 si pasa las pruebas de conversión de Docling |
| P2 | pydantic / pydantic-settings | 2.10.6 / 2.7.1 | [2.14.1](https://pypi.org/project/pydantic/2.14.1/) / [2.16.2](https://pypi.org/project/pydantic-settings/2.16.2/) | Ambas versiones; modernizar la configuración |
| P2 | numpy / pandas | 1.26.4 / 2.1.4 | [2.5.4](https://pypi.org/project/numpy/2.5.4/) / [3.1.0](https://pypi.org/project/pandas/3.1.0/) | Candidatas transitivas, validar modelos y conversión |
| P2 | Pillow | 10.4.0 | [13.0.0](https://pypi.org/project/pillow/13.0.0/) | [12.3.0](https://pypi.org/project/pillow/12.3.0/), porque Gradio exige <13 |
| P2 | python-dotenv | 1.0.1 | [1.2.4](https://pypi.org/project/python-dotenv/1.2.4/) | 1.2.4, si se fija explícitamente |
| P3 | loguru | 0.7.3 | [0.7.3](https://pypi.org/project/loguru/0.7.3/) | Conservar |
| P3 | rank-bm25 | 0.2.2 | [0.2.2](https://pypi.org/project/rank-bm25/0.2.2/) | Conservar y declarar como dependencia funcional |

## Restricciones que impiden actualizar todo a la última versión

1. **Groq:** `langchain-groq==1.1.3` exige `groq>=0.30,<1`. Aunque el SDK Groq
   tiene la versión estable 1.7.0, el candidato compatible es `groq==0.37.1`.
2. **Imágenes:** `gradio==6.31.0` exige `Pillow<13`; el candidato es 12.3.0.
3. **Hugging Face:** `docling-ibm-models==4.0.4` exige `huggingface-hub<2`,
   y Gradio exige `>=1.16,<3`. La intersección admite
   `huggingface-hub==1.33.0`; la última estable 2.3.0 no satisface ambos paquetes.
4. **Pydantic:** 2.14.1 exige exactamente `pydantic-core==2.50.1`. Mantener el
   pin antiguo 2.27.2 impediría esa actualización.
5. **PDF:** el nuevo Docling excluye `pypdfium2==4.30.1`, que está fijado en
   ambos archivos actuales. El inventario muestra 5.14.0 como candidata.
6. **Docling:** 2.144.0 depende de `docling-slim[standard]==2.144.0`.
   Sus restricciones actuales requieren renovar también docling-core,
   docling-parse y docling-ibm-models. Las candidatas observadas son 2.105.0,
   7.24.1 y 4.0.4 respectivamente. No se deben conservar los pins antiguos al
   actualizar solo el paquete superior.
7. **Windows:** las distribuciones consultadas de PyTorch y torchvision tienen
   wheels Windows, pero no wheels CPython 3.15. uvloop y nvidia-nccl-cu12 no
   publican wheels Windows en las versiones consultadas. No se debe usar el
   mismo bloqueo Linux/CUDA sin marcadores para Windows.
8. **LangGraph:** 1.2.18 exige `langgraph-checkpoint>=4.3,<5` y
   `langgraph-sdk>=0.4.6,<0.5`; los pins 2.0.10 y 0.1.51 deben renovarse juntos.

Las restricciones se obtuvieron de `requires_dist` en PyPI y se guardaron en
el JSON de evidencia. La compatibilidad de versiones declarada por metadatos no
garantiza compatibilidad de comportamiento ni disponibilidad de cada wheel CPU/CUDA.

## Motivos de seguridad para la prioridad

- [Gradio GHSA-39mp-8hj3-5c49](https://github.com/gradio-app/gradio/security/advisories/GHSA-39mp-8hj3-5c49):
  lectura de archivos mediante traversal en Windows/Python 3.13+, corregida en
  6.7.0. La versión declarada 5.13.2 entra en el rango afectado y el equipo usa
  Windows/Python 3.15. También hay avisos relacionados con carga multipart.
- [h11 GHSA-vqfr-h8mv-ghfj](https://github.com/python-hyper/h11/security/advisories/GHSA-vqfr-h8mv-ghfj):
  procesamiento HTTP susceptible a request smuggling bajo determinadas
  combinaciones de proxy/servidor, corregido en 0.16.0.
- [LangChain GHSA-c67j-w6g6-q2cm](https://github.com/langchain-ai/langchain/security/advisories/GHSA-c67j-w6g6-q2cm):
  inyección en serialización que puede extraer secretos en rutas de dumps/loads;
  el aviso incluye la versión declarada de langchain-core. Los primeros parches
  fueron 0.3.81 y 1.2.5, pero no son una recomendación global de versión segura:
  existen avisos posteriores y debe auditarse el bloqueo final.
- [LangGraph GHSA-g48c-2wqr-h844](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-g48c-2wqr-h844):
  carga insegura de checkpoints msgpack, corregida en 1.0.10. La aplicación no
  configura persistencia de checkpoints en su flujo actual; la alcanzabilidad
  debe distinguirse de la coincidencia por versión.

El índice de severidad se usa para ordenar trabajo; no se concluye que DocChat
haya sido comprometido. Su `share=True` hace especialmente relevante revisar la
superficie HTTP y la carga de documentos antes de publicar un entorno renovado.

## Cambios de código necesarios

- `app.py`: mover `theme`, `css` y `js` de `gr.Blocks(...)` a
  `demo.launch(...)`, conforme a la migración de Gradio 6. Probar carga de
  archivos y los accesos `file.name` con los valores que devuelve la nueva UI.
- `agents/workflow.py` y `retriever/builder.py`: importar `EnsembleRetriever`
  desde `langchain_classic.retrievers`. En el estado actual se importa desde
  `langchain.retrievers`, que no conserva esa API en la rama 1.x.
- `config/settings.py`: reemplazar `class Config` por
  `model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")`
  y probar carga de las dos claves desde entorno y `.env`.
- `config/llm.py`: conservar el modelo solicitado `llama-3.1-8b-instant`,
  temperatura 0.5 y límite 256. La renovación de bibliotecas no requiere cambiar
  esos valores. Probar la respuesta real de ChatGroq y su campo `content`.
- `retriever/builder.py`: mantener el mismo modelo de embeddings durante la
  migración inicial; probar recuperación e indexación usando una copia del
  almacenamiento Chroma. Si se cambia el modelo o su dimensión, reconstruir
  el índice en una colección nueva.
- `document_processor/file_handler.py`: probar conversión, encabezados,
  fragmentación y caché con la nueva familia Docling. Usar una caché separada
  para evitar reutilizar objetos serializados del entorno anterior.

Actualizar bibliotecas no corrige automáticamente los defectos de verificación
identificados en la revisión previa: detección de resultados negativos por
texto formateado, claves inconsistentes y ausencia de la pregunta original en
el verificador. Conviene tratarlos como correcciones funcionales separadas.

## Solución propuesta

1. **Establecer la plataforma:** Python 3.12 con su último parche disponible;
   comenzar con CPU en Windows. Crear el entorno en paralelo al actual.
2. **Definir dependencias directas:** Gradio, Docling, langchain-core,
   langchain-classic, langchain-community, langchain-groq,
   langchain-google-genai, langchain-chroma, langchain-text-splitters,
   LangGraph, pydantic-settings, Loguru y rank-bm25. Declarar torch/torchvision
   por perfil para controlar el origen CPU o CUDA. Pydantic y algunas
   restricciones transitivas pueden fijarse por política de compatibilidad.
3. **Retirar raíces sin uso confirmado:** langchain-cohere, langchain-ibm,
   langchain-openai y unstructured no se importan directamente en el código
   revisado. Eliminar su condición de dependencia raíz si no hay otros
   consumidores; conservar cualquier paquete que aún resulte necesario de
   forma transitiva. No eliminar manualmente bibliotecas solo porque no se
   importan desde el código de aplicación.
4. **Resolver el árbol completo:** usar `pyproject.toml` y un bloqueo con `uv`,
   o un archivo de entradas y bloqueos generados con pip-tools. Mantener
   distinción entre entradas mantenidas y resolución exacta con hashes. Las
   versiones candidatas de este informe son la entrada de esa resolución,
   no un sustituto de ella.
5. **Separar perfiles:** producir y verificar instalaciones Windows/CPU y,
   cuando se conozcan GPU y controlador, Linux o Windows/CUDA. Elegir la
   distribución PyTorch según el selector oficial. Dejar que PyTorch resuelva
   sus librerías NVIDIA, con los marcadores de plataforma que correspondan.
6. **Migrar el código** de interfaz, retrievers y configuración junto con
   sus familias de paquetes, siguiendo los cambios anteriores.
7. **Validar:** resolución satisfactoria, instalación desde cero, `pip check`,
   auditoría del bloqueo con pip-audit u OSV y pruebas reales de carga PDF,
   DOCX, TXT y Markdown; caché, BM25, Chroma, clasificación, respuesta y
   verificación. Repetir con CUDA si ese perfil se va a distribuir.
8. **Criterio de aceptación:** ambos perfiles elegidos se instalan desde el
   bloqueo, no hay incompatibilidades declaradas, los avisos abiertos se han
   resuelto o documentado por alcanzabilidad y el flujo completo conserva
   sus resultados esperados.

No se modificaron los archivos de requisitos ni el código de aplicación durante
esta revisión. No se instalaron las candidatas ni se ejecutó el flujo contra
Groq/Gemini; queda pendiente demostrar la resolución completa y el comportamiento
real antes de aprobar esas versiones como el bloqueo de producción.

## Referencias de migración

- [LangChain v1](https://docs.langchain.com/oss/python/migrate/langchain-v1).
- [LangGraph v1](https://docs.langchain.com/oss/python/migrate/langgraph-v1).
- [Gradio 6](https://gradio.app/guides/gradio-6-migration-guide).
- [Migraciones Chroma](https://docs.trychroma.com/docs/overview/migration).
- [PyTorch por plataforma](https://pytorch.org/get-started/locally/).
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).
