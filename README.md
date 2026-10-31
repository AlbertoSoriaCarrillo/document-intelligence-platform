# Extracción de facturas — Prueba técnica Zebra

Aplicación con backend Python/FastAPI y frontend Angular para subir una factura PDF, extraer sus campos y mostrarlos junto a su estado: encontrado, dudoso o no encontrado.

## Alcance

El prototipo admite PDF con capa de texto y estructura compatible con la factura ficticia Lumenia incluida en `docs/factura_luz_simulada_lumenia.pdf`.

Los valores se extraen del contenido: no dependen del nombre del archivo ni están prefijados. Pueden cambiar fechas, identificadores, cantidades e importes dentro de la estructura admitida.

No admite imágenes, PDF escaneados ni diseños arbitrarios. No requiere Tesseract, servicios externos de IA ni claves API.

## Requisitos

- Python 3.13 y Node.js 24 son las versiones utilizadas durante el desarrollo.
- npm.
- Dos terminales: una para el backend y otra para Angular.

Los siguientes comandos están preparados para PowerShell.

## Instalación y arranque

Clonar el repositorio:

```powershell
git clone https://github.com/AlbertoSoriaCarrillo/document-intelligence-platform.git
Set-Location document-intelligence-platform
```

### Backend

Desde la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend-python --reload --port 8000
```

No es necesario activar el entorno virtual al utilizar directamente su ejecutable.

- Documentación de la API: http://localhost:8000/docs
- Estado del servicio: http://localhost:8000/api/health

### Frontend

En otra terminal, desde la raíz del repositorio:

```powershell
Set-Location frontend-angular
npm ci
npm start
```

Abrir http://localhost:4200.

Seleccionar el PDF de `docs/`, pulsar **Extraer datos** y revisar los campos y conceptos.

La muestra contiene cinco conceptos, una base imponible de **52,29 EUR**, un IVA de **10,98 EUR** y un total de **63,27 EUR**. El texto «Cuota de ejemplo» se marca como dudoso porque no representa un precio numérico.

## Configuración

La dirección del backend se configura mediante `apiUrl` en:

- `frontend-angular/src/environments/environment.development.ts`: desarrollo.
- `frontend-angular/src/environments/environment.ts`: compilación de producción.

Ambos entornos apuntan inicialmente a `http://localhost:8000`. Los valores se incorporan al compilar; no deben contener secretos.

El backend permite peticiones desde `http://localhost:4200` mediante CORS. Si cambia el origen de la interfaz, deberá actualizarse esa configuración.

Los textos de la interfaz están en `frontend-angular/src/app/resources/ui-texts.ts`
y se incorporan al compilar. Los mensajes del backend están en
`backend-python/app/resources/messages.json`; se cargan al iniciar el proceso,
por lo que hay que reiniciar el backend para aplicar sus cambios.

Las dependencias Python se mantienen en `backend-python/requirements.txt`. El archivo de la raíz referencia esa lista.

## API y esquema de salida

- `GET /api/health`: estado del servicio.
- `POST /api/documents/inspect`: subida multipart con el campo `file`.
- Tamaño máximo: 10 MiB.

La respuesta incluye:

- Metadatos: `filename`, `content_type`, `size`, `character_count`.
- Método: `extraction_method`.
- Vista previa y avisos: `text_preview`, `warnings`.
- Datos estructurados: `extracted_fields`.

Campos extraídos:

| Campo | Significado |
|---|---|
| `invoice_number` | Número de factura |
| `issue_date` | Fecha de emisión |
| `issuer_tax_id` | NIF/CIF del emisor |
| `recipient_tax_id` | NIF/CIF del receptor |
| `subtotal` | Base imponible |
| `tax` | Importe del IVA |
| `total` | Importe total |
| `currency` | Moneda |
| `line_items` | Lista de conceptos |

Cada campo simple contiene `value` y `status`:

```json
{
  "value": "63.27",
  "status": "found"
}
```

Los estados son:

- `found`: valor extraído; no implica validación fiscal ni autenticidad.
- `doubtful`: valor que requiere revisión.
- `missing`: valor no encontrado, representado como `null`.

`line_items.value` es una lista o `null`. Cada concepto contiene `description`, `quantity`, `unit_price` y `amount`, todos con su propio valor y estado. La lista también dispone de un estado global.

Las cantidades y precios conservan sus unidades y expresiones originales. Los importes normalizados se representan como cadenas con punto decimal.

## Manejo de errores

El backend comprueba el contenido del archivo, no solo su nombre o MIME.

Devuelve errores explícitos para archivos vacíos, demasiado grandes, corruptos, protegidos que no puedan leerse, páginas sin texto y estructuras incompatibles.

En documentos compatibles, los campos ausentes o ambiguos se muestran con su estado correspondiente. La interfaz también informa de fallos de conexión y permite reintentar.

## Pruebas

Backend, desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Frontend, desde `frontend-angular`:

```powershell
npm test -- --watch=false
npm run build
```

Las pruebas cubren extracción de la muestra, valores alternativos, campos ausentes, separación de emisor y receptor, errores de archivo y comportamiento de la interfaz.

## Organización

- `backend-python/app/api/`: endpoints HTTP.
- `backend-python/app/core/`: configuración y carga de mensajes.
- `backend-python/app/resources/`: mensajes del backend en JSON.
- `backend-python/app/extraction/`: lectura del PDF y extracción de campos y conceptos.
- `backend-python/app/models/`: modelos de respuesta.
- `backend-python/tests/`: pruebas del backend.
- `frontend-angular/`: interfaz, servicio HTTP y pruebas.
- `docs/`: documento ficticio de prueba.

Las instrucciones específicas de cada componente están en el
[README del backend](backend-python/README.md) y el
[README del frontend](frontend-angular/README.md).

## Decisiones y limitaciones

Se eligió extracción local mediante PyMuPDF y reglas explícitas porque el alcance permite trabajar con una estructura conocida y PDF con capa de texto. La privacidad y el control de los datos motivan esta decisión: el procesamiento se realiza en el backend, sin enviar las facturas ni su contenido a servicios externos de modelos de lenguaje (LLM). Esto evita una exposición adicional de datos privados a terceros y permite controlar las reglas de extracción, además de evitar costes y dependencias de una API externa. No supone una garantía absoluta de seguridad: en un despliegue real también deben protegerse el transporte, los accesos y los registros.

La versión actual no utiliza OCR: lee directamente el texto incorporado en el PDF. Para una futura ampliación a documentos escaneados, podría utilizarse OCR local manteniendo el criterio de no enviar datos a terceros. Un LLM puede ayudar con diseños variables, pero un servicio externo requeriría evaluar el tratamiento de datos y las condiciones del proveedor; un modelo local sería una alternativa con otros requisitos de recursos y mantenimiento.

Durante el desarrollo se exploró un alcance mayor y se redujo para priorizar el flujo completo solicitado y facilitar su explicación.

La solución depende del orden de lectura y de los encabezados de la muestra. No reconstruye tablas arbitrarias ni garantiza interpretar otras plantillas. No valida autenticidad, dígitos de control fiscales ni coherencia aritmética de los importes.

Con más tiempo, priorizaría pruebas con más variantes de la estructura admitida, validaciones aritméticas y una mejor representación de unidades y cálculos. Para producción también revisaría los límites de procesamiento, concurrencia, observabilidad y necesidades de control de acceso.

## Uso de IA durante el desarrollo

Se utilizaron ChatGPT y Codex como apoyo para analizar los requisitos, proponer la estructura del proyecto, generar y revisar partes del código, preparar pruebas y resolver errores. También se emplearon para explicar conceptos de Python y Angular, crear documentos ficticios de prueba y revisar la documentación. Codex realizó ajustes concretos de refactorización y limpieza del backend y del frontend.

Las decisiones finales sobre el alcance funcional y el enfoque técnico fueron del autor del proyecto. La IA aportó recomendaciones y realizó cambios de implementación dentro de las tareas autorizadas; sus propuestas se revisaron y adaptaron al alcance de la prueba. La responsabilidad de aceptar los cambios y de la solución entregada corresponde al autor.

El desarrollo fue incremental y se comprobó mediante tests y pruebas manuales. Se descartaron funcionalidades adicionales para centrar la solución en facturas PDF con la estructura de la muestra Lumenia.

La IA se utilizó como herramienta de desarrollo; no interviene en la extracción de datos durante la ejecución de la aplicación.
