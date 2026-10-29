import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';

import { App } from './app';
import { DocumentInspectionResponse } from './models/document.model';

describe('Extracción de facturas', () => {
  let fixture: ComponentFixture<App>;
  let http: HttpTestingController;
  let page: HTMLElement;

  const endpoint = 'http://localhost:8000/api/documents/inspect';

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(App);
    http = TestBed.inject(HttpTestingController);
    page = fixture.nativeElement;
    fixture.detectChanges();
  });

  afterEach(() => {
    http.verify();
  });

  function selectFile(file: File): void {
    const input = page.querySelector<HTMLInputElement>(
      'input[type="file"]',
    )!;

    Object.defineProperty(input, 'files', {
      configurable: true,
      value: [file],
    });

    input.dispatchEvent(new Event('change'));
    fixture.detectChanges();
  }

  function submit(): void {
    page.querySelector<HTMLButtonElement>('button')!.click();
    fixture.detectChanges();
  }

  function selectPdf(): File {
    const file = new File(['contenido de prueba'], 'factura.pdf', {
      type: 'application/pdf',
    });

    selectFile(file);
    return file;
  }

  it('muestra el título y deshabilita el envío sin archivo', () => {
    expect(page.querySelector('h1')?.textContent)
      .toContain('Extracción de facturas');

    expect(page.querySelector<HTMLButtonElement>('button')!.disabled)
      .toBe(true);

    http.expectNone(endpoint);
  });

  it('rechaza un archivo que no sea PDF', () => {
    selectFile(new File(['imagen'], 'foto.jpg'));

    expect(page.querySelector('[role="alert"]')?.textContent)
      .toContain('Selecciona un archivo PDF.');

    expect(fixture.componentInstance.selectedFile()).toBeNull();
    http.expectNone(endpoint);
  });

  it('rechaza un archivo vacío', () => {
    selectFile(new File([], 'vacio.pdf'));

    expect(page.querySelector('[role="alert"]')?.textContent)
      .toContain('El archivo está vacío.');

    http.expectNone(endpoint);
  });

  it('rechaza un archivo superior a 10 MB', () => {
    const file = new File(
      [new Uint8Array(10 * 1024 * 1024 + 1)],
      'grande.pdf',
    );

    selectFile(file);

    expect(page.querySelector('[role="alert"]')?.textContent)
      .toContain('El archivo no puede superar los 10 MB.');

    http.expectNone(endpoint);
  });

  it('envía el PDF y muestra los datos y sus estados', () => {
    const file = selectPdf();
    submit();

    expect(page.querySelector<HTMLButtonElement>('button')!.disabled)
      .toBe(true);

    expect(page.querySelector('[role="status"]')?.textContent)
      .toContain('Leyendo la factura');

    const request = http.expectOne(endpoint);

    expect(request.request.method).toBe('POST');
    expect(request.request.body instanceof FormData).toBe(true);
    expect(request.request.body.get('file')).toBe(file);
    expect(request.request.headers.has('Content-Type')).toBe(false);

    const response: DocumentInspectionResponse = {
      filename: 'factura.pdf',
      content_type: 'application/pdf',
      size: file.size,
      character_count: 100,
      extraction_method: 'native_text',
      extracted_fields: {
        invoice_number: { value: 'TEST-001', status: 'found' },
        issue_date: { value: '29/10/2026', status: 'found' },
        issuer_tax_id: { value: 'B00000000', status: 'found' },
        recipient_tax_id: { value: null, status: 'missing' },
        subtotal: { value: '10.00', status: 'found' },
        tax: { value: '2.10', status: 'found' },
        total: { value: '12.10', status: 'found' },
        currency: { value: 'EUR', status: 'found' },
        line_items: {
          value: [{
            description: { value: 'Servicio demo', status: 'found' },
            quantity: { value: null, status: 'missing' },
            unit_price: { value: 'Cuota de ejemplo', status: 'doubtful' },
            amount: { value: '10.00', status: 'found' },
          }],
          status: 'doubtful',
        },
      },
      text_preview: '',
      warnings: [],
    };

    request.flush(response);
    fixture.detectChanges();

    expect(page.textContent).toContain('TEST-001');
    expect(page.textContent).toContain('12.10');
    expect(page.querySelector('tbody')?.textContent)
      .toContain('Servicio demo');
    expect(page.querySelector('tbody')?.textContent)
      .toContain('Revisar');
    expect(page.querySelector('tbody')?.textContent)
      .toContain('No encontrado');

    expect(page.querySelector<HTMLButtonElement>('button')!.disabled)
      .toBe(false);
  });

  it('muestra el error del backend y permite reintentar', () => {
    selectPdf();
    submit();

    http.expectOne(endpoint).flush(
      { detail: 'El PDF no contiene texto extraíble.' },
      { status: 422, statusText: 'Unprocessable Content' },
    );

    fixture.detectChanges();

    expect(page.querySelector('[role="alert"]')?.textContent)
      .toContain('El PDF no contiene texto extraíble.');

    expect(page.querySelector<HTMLButtonElement>('button')!.disabled)
      .toBe(false);

    expect(fixture.componentInstance.result()).toBeNull();
  });

  it('avisa cuando no puede conectar con el backend', () => {
    selectPdf();
    submit();

    http.expectOne(endpoint).error(new ProgressEvent('error'));
    fixture.detectChanges();

    expect(page.querySelector('[role="alert"]')?.textContent)
      .toContain('No se pudo conectar con el servidor.');

    expect(page.querySelector<HTMLButtonElement>('button')!.disabled)
      .toBe(false);
  });
});