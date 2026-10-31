# Backend de facturas

API FastAPI limitada a PDF con capa de texto y estructura de la
[factura ficticia Lumenia](../docs/factura_luz_simulada_lumenia.pdf).
La lectura y extracción se realizan localmente con PyMuPDF y reglas explícitas.

## Instalación y ejecución

Se utiliza Python 3.13. Desde la raíz del repositorio, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend-python --reload --port 8000
```

Si ya existe el entorno, no hace falta crearlo de nuevo. La documentación
interactiva está en http://localhost:8000/docs.

`backend-python/requirements.txt` mantiene las dependencias; el archivo de la raíz
referencia esa lista. Incluye pytest y httpx para las pruebas. La versión declarada
de PyMuPDF es 1.26.7. No se requieren OCR, Tesseract ni servicios externos de IA.

## Configuración y organización

- `app/main.py`: creación de la aplicación, CORS y comprobación de salud.
- `app/api/`: recepción de archivos y respuestas HTTP.
- `app/core/config.py`: límite de tamaño del archivo.
- `app/core/messages.py`: carga y consulta de mensajes.
- `app/resources/messages.json`: mensajes de error y avisos; reiniciar el backend tras modificarlos.
- `app/extraction/`: lectura del PDF, comprobación de estructura y extracción de campos y conceptos.
- `app/models/`: modelos Pydantic de la respuesta y estados de extracción.
- `tests/`: pruebas de los extractores, endpoints y esquema de la API.

Los mensajes JSON deben conservar las claves utilizadas por el código. Se cargan
una vez por proceso. La configuración actual no lee archivos `.env`.

## API y respuesta

- `GET /api/health`: estado del servicio.
- `POST /api/documents/inspect`: multipart con campo `file`, máximo 10 MiB.
- CORS permite `http://localhost:4200`.

El contenido se abre como PDF; extensión, MIME, nombre y hash no determinan su
compatibilidad. Errores: 400 vacío, 413 tamaño excedido y 422 contenido no PDF,
corrupto, protegido con contraseña, página sin texto o estructura incompatible.

La respuesta conserva `filename`, `content_type` (PDF validado), `size`,
`character_count`, `extraction_method` (`native_text`), `text_preview`, `warnings`
y `extracted_fields`.

Campos: `invoice_number`, `issue_date`, `issuer_tax_id`, `recipient_tax_id`,
`subtotal` (base imponible), `tax` (importe IVA), `total`, `currency`, `line_items`.
Cada campo contiene `value` y `status`: `found`, `doubtful` o `missing`.
Ausencias usan `null`; candidatos contradictorios se muestran separados por ` | `
y como dudosos. `found` expresa extracción inequívoca, no validación fiscal del NIF.
Los importes usan punto decimal. Moneda EUR solo cuando aparece EUR o el símbolo euro.

`line_items.value` contiene conceptos con `description`, `quantity`, `unit_price`
y `amount`, cada uno con su estado. Conserva cantidades ausentes (`-`). Los precios
explicativos quedan dudosos y propagan ese estado a `line_items`.

## Límites y pruebas

Se requieren los encabezados Factura, Emisor, Receptor, Detalle de la factura y la
tabla Concepto / Cantidad / Precio / cálculo / Importe en orden de lectura de texto
como la muestra. Los valores pueden variar o faltar. No se reconstruyen columnas
por coordenadas ni filas cuyo texto ya no permita identificar cuatro celdas;
una tabla incompleta se marca dudosa. No admite imágenes, escaneos ni otros diseños.
No calcula valores ausentes ni valida sumas, controles fiscales o autenticidad.

Desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Las pruebas cubren la muestra ficticia (cinco conceptos y totales), valores alternativos,
ausencias, candidatos ambiguos, separación de partes, falsos números de factura,
errores de archivo, límite de tamaño, salud y CORS.
