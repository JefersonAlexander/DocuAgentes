# Embeddings locales y documentos grandes

La aplicación usa `langchain_huggingface.HuggingFaceEmbeddings`, la integración
actual de LangChain, y `sentence-transformers` sobre Python 3.12.
Gemini dejó de ser necesario para indexación y consulta; la clave Groq sigue
siendo necesaria para los tres agentes. Las claves reales de `.env` se conservan.

## Modelos evaluados por documentación

| Modelo | Licencia | Máximo por fragmento | Dimensiones | Uso propuesto |
|---|---|---|---|---|
| intfloat/multilingual-e5-small | MIT | 512 tokens | 384 | Predeterminado para CPU y español |
| BAAI/bge-m3 | MIT | 8192 tokens | 1024 | Alternativa para fragmentos más amplios y mayor capacidad de cómputo |
| Qwen/Qwen3-Embedding-0.6B | Apache 2.0 | 32K tokens | Hasta 1024 | Alternativa revisada, no integrada en esta implementación |

El máximo corresponde a cada entrada del encoder, no al documento completo.
Un documento extenso se representa con varios vectores. Aumentar la ventana
del encoder no sustituye automáticamente la división por secciones ni garantiza
una recuperación más precisa para preguntas concretas.

Se eligió E5-small como predeterminado por la instalación CPU ya existente.
BGE-M3 queda disponible mediante `.env`, sin obligar a descargar su modelo mayor
en este equipo. La decisión es una selección de arquitectura y recursos;
no se ha realizado un benchmark comparativo sobre un corpus representativo.

## Implementación

- `retriever/embeddings.py` reutiliza el modelo y su tokenizer desde caché.
- Los prefijos E5 se aplican únicamente al cálculo de embeddings: `passage: `
  para documentos y `query: ` para preguntas. El texto que reciben los agentes
  permanece sin esos prefijos.
- Los embeddings se normalizan. BGE-M3 utiliza aquí únicamente vectores densos
  y mantiene BM25 como componente léxico de la búsqueda híbrida.
- Los documentos se convierten con Docling, se separan por encabezados y se
  subdividen con el tokenizer correspondiente. La configuración predeterminada
  es 448 tokens con solapamiento de 64 para E5.
- Se reserva espacio para prefijos y tokens especiales y se comprueba el límite
  de cada entrada. Una configuración de tamaños incompatible se rechaza.
- El modelo y los tamaños forman parte del identificador de colección y caché.
  Los índices anteriores se conservan y no reciben vectores de otra dimensión.
- El SDK de Google dejó de ser una dependencia raíz y se regeneraron los
  archivos de requisitos de CPU y CUDA desde `uv.lock`.
- `.env.example` se dejó como plantilla sin credenciales reales. `.env` no se
  modificó; su campo Gemini anterior, si existe, se acepta y no se utiliza.

## Validación realizada

- Python 3.12.16; 194 distribuciones instaladas compatibles según `uv pip check`.
- Bloqueo consistente y simulación del perfil CUDA resuelta.
- 19 pruebas aprobadas, incluidas las integraciones previas y cuatro pruebas
  de embeddings locales y fragmentación.
- E5 se descargó en el proyecto y produjo vectores normalizados de 384
  dimensiones. Una consulta de recuperación de contraseña en español ordenó
  el pasaje pertinente por encima de un pasaje de mantenimiento de cámaras.
- Un documento sintético con 500 procedimientos se dividió en 14 fragmentos,
  conservando sus marcadores inicial y final, los encabezados y el nombre de
  origen. Todos los fragmentos respetaron el presupuesto de tokens.
- Se comprobaron los prefijos E5, las opciones sin prefijos de BGE y el cambio
  de identificador de índice/caché al cambiar modelo o tamaños.
- BGE-M3 no se descargó ni se ejecutó; no se validó GPU ni se consumió Groq.

## Fuentes

- [E5-small: ficha y requisitos de prefijos](https://huggingface.co/intfloat/multilingual-e5-small/raw/main/README.md).
- [BGE-M3: ventana, idiomas y uso de vectores densos](https://huggingface.co/BAAI/bge-m3).
- [Qwen3 Embedding 0.6B: contexto y licencia](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B).
- [Integración Sentence Transformers de LangChain](https://docs.langchain.com/oss/python/integrations/embeddings/sentence_transformers).
