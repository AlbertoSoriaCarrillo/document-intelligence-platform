# Frontend de extracción de facturas

Interfaz Angular de una sola pantalla para subir una factura PDF compatible con
la muestra Lumenia y consultar los campos y conceptos devueltos por el backend.

## Instalación y arranque

Se utiliza Node.js 24 y npm. Desde esta carpeta (`frontend-angular`):

```powershell
npm ci
npm start
```

Abrir http://localhost:4200. Para procesar documentos debe estar arrancado el
backend; consulta las instrucciones del [README principal](../README.md).

## Probar el flujo

1. Seleccionar [la factura de muestra](../docs/factura_luz_simulada_lumenia.pdf).
2. Pulsar **Extraer datos**.
3. Revisar los campos y los cinco conceptos, incluidos sus estados.

La interfaz comprueba extensión PDF, archivo no vacío y un máximo de 10 MiB.
El backend valida el contenido y la estructura. No se admiten imágenes, PDF
escaneados ni plantillas arbitrarias.

Los estados se muestran como **Encontrado**, **Revisar** y **No encontrado**.
Encontrado significa extraído, no validado fiscalmente. Los valores ausentes
se muestran como un guion. Los errores permiten volver a intentar la operación.

## Configuración y textos

- `src/environments/environment.development.ts`: dirección `apiUrl` para desarrollo.
- `src/environments/environment.ts`: dirección `apiUrl` para producción.
- `src/app/resources/ui-texts.ts`: textos, etiquetas y errores locales de la interfaz.

Ambos entornos apuntan inicialmente a `http://localhost:8000`. Estos valores y
los textos se incorporan al compilar. Si cambia el origen del frontend, debe
ajustarse también CORS en el backend. Los errores y avisos recibidos de la API
se muestran con el texto que envía el servidor. La aplicación tiene un único
idioma; centralizar los textos no incorpora traducción automática.

## Organización

- `src/app/app.ts`: selección de archivo, estado de la pantalla y envío de peticiones.
- `src/app/app.html` y `app.scss`: presentación y estilos de la pantalla.
- `src/app/services/document.service.ts`: comunicación HTTP con la API.
- `src/app/models/document.model.ts`: contrato TypeScript de la respuesta.
- `src/app/resources/ui-texts.ts`: textos visibles.
- `src/app/app.spec.ts`: pruebas del componente con respuestas HTTP simuladas.

No hay navegación entre pantallas ni configuración de router.

## Pruebas y compilación

Desde esta carpeta:

```powershell
npm test -- --watch=false
npm run build
```

Las pruebas cubren selección y validación de archivos, presentación de resultados
y manejo de errores del backend y de conexión. No hay pruebas E2E configuradas;
el flujo con la API real se comprueba manualmente con la muestra.

La compilación genera la aplicación en `dist/document-intelligence-ui/`.
Compilar no arranca ni publica el backend.
