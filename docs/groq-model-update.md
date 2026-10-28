# Corrección del modelo Groq y de los errores de relevancia

Fecha: 28 de octubre de 2026.

La aplicación conservaba `llama-3.1-8b-instant` como modelo fijo. Groq anunció
su retirada para cuentas gratuitas y de desarrollador el 16 de agosto de 2026,
con `openai/gpt-oss-20b` como reemplazo recomendado.

Se consultó el catálogo usando la clave configurada sin mostrarla ni enviar
documentos: GPT-OSS 20B y 120B aparecían disponibles; Llama 3.1 8B Instant no.

## Cambios

- `GROQ_MODEL` selecciona el modelo; predeterminado: `openai/gpt-oss-20b`.
- `GROQ_MAX_TOKENS` controla el presupuesto; predeterminado: 1024. Se amplió
  respecto a los 256 anteriores para reservar espacio al razonamiento y a la
  respuesta final del reemplazo.
- Para GPT-OSS 20B/120B se configura esfuerzo bajo y `include_reasoning=False`.
  No se utiliza `reasoning_format`, que Groq no admite para estos modelos.
- Los tres agentes utilizan el mismo manejo de errores. Un 404 señala revisar
  `GROQ_MODEL`; un 401/403, credenciales/permisos; un 429, límite de uso.
- Un fallo del proveedor o una clasificación inválida ya no se convierte en
  `NO_MATCH`. El flujo propaga el error a la interfaz sin afirmar que el
  documento es irrelevante.
- Se actualizaron la plantilla y README. La clave real de `.env` se conserva;
  al no existir una selección explícita de modelo se utiliza el nuevo valor
  predeterminado después de reiniciar la aplicación.

## Validación

La prueba real con Groq completó clasificación, generación y verificación con
un párrafo sintético sobre registro y resolución de incidentes de seguridad.
No se enviaron archivos ni contenido documental del usuario.

La suite completa finalizó con 22 pruebas aprobadas en Python 3.12.16.

Se agregaron comprobaciones de selección de modelo/presupuesto, traducción de
errores HTTP y un caso de regresión que reproduce un 404: la investigación no
se ejecuta y se propaga el error de configuración en lugar de devolver una
clasificación negativa del documento.

## Fuentes

- [Retiradas y reemplazos oficiales](https://console.groq.com/docs/deprecations).
- [Modelos disponibles y consulta del catálogo](https://console.groq.com/docs/models).
- [Razonamiento: parámetros específicos de GPT-OSS](https://console.groq.com/docs/reasoning).
