export type FieldStatus = 'found' | 'doubtful' | 'missing';

export interface ExtractedField {
  value: string | null;
  status: FieldStatus;
}

export interface InvoiceLineItem {
  description: ExtractedField;
  quantity: ExtractedField;
  unit_price: ExtractedField;
  amount: ExtractedField;
}

export interface ExtractedLineItems {
  value: InvoiceLineItem[] | null;
  status: FieldStatus;
}

export interface InvoiceFields {
  invoice_number: ExtractedField;
  issue_date: ExtractedField;
  issuer_tax_id: ExtractedField;
  recipient_tax_id: ExtractedField;
  subtotal: ExtractedField;
  tax: ExtractedField;
  total: ExtractedField;
  currency: ExtractedField;
  line_items: ExtractedLineItems;
}

export interface DocumentInspectionResponse {
  filename: string;
  content_type: string;
  size: number;
  character_count: number;
  extraction_method: string;
  extracted_fields: InvoiceFields;
  text_preview: string;
  warnings: string[];
}