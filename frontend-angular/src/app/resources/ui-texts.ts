/** Textos de la pantalla de extracción de facturas. */
export const UI_TEXTS = {
  title: 'Extracción de facturas',
  introduction:
    'Selecciona una factura con la estructura del ejemplo Lumenia. ' +
    'Debe ser un PDF con texto, no una imagen escaneada.',

  upload: {
    label: 'Factura en PDF',
    help: 'Tamaño máximo: 10 MB.',
    selectedFile: 'Archivo seleccionado:',
    submit: 'Extraer datos',
    processing: 'Procesando…',
  },

  processing: {
    reading: 'Leyendo la factura. Espera un momento.',
    completed: 'Procesamiento completado. Revisa los datos extraídos.',
  },

  result: {
    title: 'Resultado',
    filename: 'Archivo:',
    guidance:
      '“Encontrado” indica que el dato se ha extraído. ' +
      'Comprueba los valores con la factura original.',
    invoiceData: 'Datos de la factura',
  },

  lineItems: {
    title: 'Conceptos',
    status: 'Estado:',
    caption: 'Conceptos extraídos de la factura',
    columns: {
      description: 'Descripción',
      quantity: 'Cantidad',
      unitPrice: 'Precio unitario',
      amount: 'Importe',
    },
    empty: 'No se encontraron conceptos.',
    unavailable: 'No se pudieron extraer los conceptos.',
  },

  fieldLabels: {
    invoice_number: 'Número de factura',
    issue_date: 'Fecha de emisión',
    issuer_tax_id: 'NIF/CIF del emisor',
    recipient_tax_id: 'NIF/CIF del receptor',
    subtotal: 'Base imponible',
    tax: 'IVA',
    total: 'Total',
    currency: 'Moneda',
  },

  fieldStatus: {
    found: 'Encontrado',
    doubtful: 'Revisar',
    missing: 'No encontrado',
  },

  missingValue: '—',

  errors: {
    invalidFormat: 'Selecciona un archivo PDF.',
    emptyFile: 'El archivo está vacío.',
    fileTooLarge: 'El archivo no puede superar los 10 MB.',
    connection:
        'No se pudo conectar con el servidor. Comprueba que está arrancado.',
    processing:
        'No se pudo completar el procesamiento. Inténtalo de nuevo.',
  }
} as const;