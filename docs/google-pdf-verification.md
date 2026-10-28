# Verificación del informe ambiental de Google

Archivo: `google-2024-environmental-report.pdf`.
Fecha: 28 de octubre de 2026.

El proyecto ya utiliza Docling 2.144.0 para convertir este PDF a Markdown antes
de dividirlo y generar embeddings. No fue necesario instalar otro lector.

El archivo tiene 86 páginas y 14.845.245 bytes. Se comprobó que contiene una
capa de texto extraíble en las páginas de muestra. La conversión completa con
la configuración actual de Docling y CPU finalizó con estado `success`:

- Páginas procesadas: 86 de 86.
- Fragmentos únicos generados: 409.
- Tiempo observado de conversión y fragmentación: 302,11 segundos.
- Se preparó la caché local de la aplicación para el contenido del archivo.
- No se enviaron páginas ni fragmentos a Groq durante esta comprobación.

El tiempo observado incluye procesamiento de diseño, OCR y tablas en CPU.
Los mensajes `RapidOCR returned empty result` aparecieron durante la prueba,
pero no impidieron que finalizara. También se registró un aviso de una celda
que no pudo asignarse a la rejilla de una tabla; una conversión exitosa no
garantiza que todas las cifras/tablas se hayan reconstruido perfectamente.

## Equipo disponible

Se detectó una NVIDIA RTX A4000 con 16.376 MiB de VRAM y controlador 596.51,
además de la GPU integrada Intel UHD Graphics 630. El perfil CUDA del proyecto
utiliza PyTorch 2.14.1+cu130. El controlador detectado cumple el requisito de
la rama CUDA 13.x, que NVIDIA sitúa en la rama 580 o posterior.

La instalación CPU permanece en `.venv/`. La prueba de la variante GPU utiliza
un entorno separado `.venv-cuda/`.

## Comprobación real de GPU

- PyTorch: 2.14.1+cu130; runtime CUDA 13.0.
- `torch.cuda.is_available()`: verdadero.
- Dispositivo: NVIDIA RTX A4000.
- Se ejecutó una operación tensorial en CUDA y una consulta E5 en GPU,
  obteniendo el vector esperado de 384 dimensiones.
- Docling convirtió las páginas 1 a 3 del informe con `AcceleratorDevice.CUDA`.
  Estado: `success`; tiempo observado: 16,85 segundos, incluyendo inicialización
  de los modelos de esa conversión.
- No se repitió la conversión completa de 86 páginas con GPU. Por eso no se
  calcula un factor de aceleración a partir de estas pruebas de distinta longitud.
- RapidOCR avisó que ONNX Runtime no ofrece `CUDAExecutionProvider` en esta
  instalación y usó sus proveedores disponibles de CPU. El diseño y las tablas
  se procesaron con la configuración CUDA de Docling; no todas las fases se
  trasladan a la GPU por instalar PyTorch CUDA.

La evidencia está en [google-pdf-gpu-verification.json](google-pdf-gpu-verification.json).
El `.env` con las claves reales permanece intacto. Para iniciar el entorno GPU
desde la carpeta del proyecto:

```powershell
$env:EMBEDDING_DEVICE = "cuda"
.\.venv-cuda\Scripts\python.exe app.py
```

Referencias:

- [Conversión de documentos con Docling](https://docling-project.github.io/docling/usage/).
- [Opciones de procesamiento PDF](https://docling-project.github.io/docling/reference/pipeline_options/).
- [Compatibilidad de controladores CUDA](https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html).
