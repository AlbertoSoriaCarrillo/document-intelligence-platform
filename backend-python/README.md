# Backend de facturas

Prototipo limitado a PDF con capa de texto y estructura de la muestra Lumenia de
`docs/`. No implica que la aplicación web esté terminada. No requiere OCR,
Tesseract, modelos de idiomas ni variables de entorno. Los `.env` privados no se
leen y pueden conservarse.

## Instalación y ejecución (PowerShell, desde la raíz)

Python 3.11 o superior. Crear un entorno nuevo si se desea probar de forma aislada:

```powershell
python -m venv temp/backend-env
temp/backend-env/Scripts/python.exe -m pip install -r requirements.txt
temp/backend-env/Scripts/python.exe -m uvicorn app.main:app --app-dir backend-python
temp/backend-env/Scripts/python.exe -m pytest
```

`backend-python/requirements.txt` es la única lista de dependencias; el archivo de
la raíz la referencia. Incluye pytest y httpx para las pruebas. PyMuPDF se fija en
1.26.7 para evitar las dependencias de layout/LLM incorporadas por la versión 2.0.

## API y respuesta

- `GET /api/health`: estado del servicio.
- `POST /api/documents/inspect`: multipart con campo `file`, máximo 10 MiB.
- CORS permite `http://localhost:4200`.

El contenido se abre como PDF; extensión, MIME, nombre y hash no determinan su
compatibilidad. Errores: 400 vacío, 413 tamaño excedido y 422 contenido no PDF,
corrupto, protegido con contraseña, página sin texto o estructura incompatible.

La respuesta conserva `filename`, `content_type` (PDF validado), `size`,
`character_count`, `extraction_method` (`native_text`), `text_preview`, `warnings`
y `extracted_fields`. Ya no contiene `classification` ni `detected_tax_ids`.

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

Las pruebas cubren la muestra real (cinco conceptos y totales), valores alternativos,
ausencias, candidatos ambiguos, separación de partes, falsos números de factura,
errores de archivo, límite de tamaño, salud y CORS.
