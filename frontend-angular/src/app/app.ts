import { Component, DestroyRef, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { finalize, timeout } from 'rxjs';

import { DocumentService } from './services/document.service';
import { DocumentInspectionResponse, FieldStatus, InvoiceFields } from './models/document.model';

@Component({
  selector: 'app-root',
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  private readonly documentService = inject(DocumentService);
  private readonly destroyRef = inject(DestroyRef);

  readonly selectedFile = signal<File | null>(null);
  readonly processing = signal(false);
  readonly error = signal<string | null>(null);
  readonly result = signal<DocumentInspectionResponse | null>(null);
  readonly fieldLabels: {
    key: Exclude<keyof InvoiceFields, 'line_items'>;
    label: string;
  }[] = [
    { key: 'invoice_number', label: 'Número de factura' },
    { key: 'issue_date', label: 'Fecha de emisión' },
    { key: 'issuer_tax_id', label: 'NIF/CIF del emisor' },
    { key: 'recipient_tax_id', label: 'NIF/CIF del receptor' },
    { key: 'subtotal', label: 'Base imponible' },
    { key: 'tax', label: 'IVA' },
    { key: 'total', label: 'Total' },
    { key: 'currency', label: 'Moneda' },
  ];

  statusLabel(status: FieldStatus): string {
    const labels: Record<FieldStatus, string> = {
      found: 'Encontrado',
      doubtful: 'Revisar',
      missing: 'No encontrado',
    };

    return labels[status];
  }

  selectFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];

    this.selectedFile.set(null);
    this.result.set(null);
    this.error.set(null);

    if (!file) {
      return;
    }

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      this.error.set('Selecciona un archivo PDF.');
      input.value = '';
      return;
    }

    if (file.size === 0) {
      this.error.set('El archivo está vacío.');
      input.value = '';
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      this.error.set('El archivo no puede superar los 10 MB.');
      input.value = '';
      return;
    }

    this.selectedFile.set(file);
  }

  processDocument(): void {
    const file = this.selectedFile();

    if (!file || this.processing()) {
      return;
    }

    this.processing.set(true);
    this.error.set(null);
    this.result.set(null);

    this.documentService.inspect(file).pipe(
      timeout(30000),
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.processing.set(false)),
    ).subscribe({
      next: (response) => this.result.set(response),
      error: (error: unknown) => {
        if (error instanceof HttpErrorResponse) {
          if (error.status === 0) {
            this.error.set(
              'No se pudo conectar con el servidor. Comprueba que está arrancado.',
            );
            return;
          }

          const detail = error.error?.detail;

          if (typeof detail === 'string') {
            this.error.set(detail);
            return;
          }
        }

        this.error.set(
          'No se pudo completar el procesamiento. Inténtalo de nuevo.',
        );
      },
    });
  }
}