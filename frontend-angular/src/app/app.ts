import { Component, DestroyRef, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { finalize, timeout } from 'rxjs';
import { DocumentService } from './services/document.service';
import { DocumentInspectionResponse, FieldStatus, InvoiceFields } from './models/document.model';
import { UI_TEXTS } from './resources/ui-texts';

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
    { key: 'invoice_number', label: UI_TEXTS.fieldLabels.invoice_number },
    { key: 'issue_date', label: UI_TEXTS.fieldLabels.issue_date },
    { key: 'issuer_tax_id', label: UI_TEXTS.fieldLabels.issuer_tax_id },
    { key: 'recipient_tax_id', label: UI_TEXTS.fieldLabels.recipient_tax_id },
    { key: 'subtotal', label: UI_TEXTS.fieldLabels.subtotal },
    { key: 'tax', label: UI_TEXTS.fieldLabels.tax },
    { key: 'total', label: UI_TEXTS.fieldLabels.total },
    { key: 'currency', label: UI_TEXTS.fieldLabels.currency },
  ];
  readonly texts = UI_TEXTS;

  private readonly MAX_UPLOAD_SIZE = 10 * 1024 * 1024; // 10 MB
  private readonly REQUEST_TIMEOUT_MS = 30 * 1000; // 30 segundos

  /** Traduce el estado de la API sin alterar su significado ni depender del color. */
  statusLabel(status: FieldStatus): string {
    return this.texts.fieldStatus[status];
  }

  /** Valida la selección para orientar al usuario; el backend verifica el contenido real. */
  selectFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];

    // Evita mostrar resultados del archivo anterior tras cambiar la selección.
    this.selectedFile.set(null);
    this.result.set(null);
    this.error.set(null);

    if (!file) {
      return;
    }

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      this.error.set(this.texts.errors.invalidFormat);
      input.value = '';
      return;
    }

    if (file.size === 0) {
      this.error.set(this.texts.errors.emptyFile);
      input.value = '';
      return;
    }

    if (file.size > this.MAX_UPLOAD_SIZE) {
      this.error.set(this.texts.errors.fileTooLarge);
      input.value = '';
      return;
    }

    this.selectedFile.set(file);
  }

  /** Envía el PDF y actualiza carga, resultado y errores, permitiendo reintentar. */
  processDocument(): void {
    const file = this.selectedFile();

    if (!file || this.processing()) {
      return;
    }

    this.processing.set(true);
    this.error.set(null);
    this.result.set(null);

    this.documentService.inspect(file).pipe(
      // Limita la espera del cliente; no garantiza cancelar el trabajo del servidor.
      timeout(this.REQUEST_TIMEOUT_MS),
      // Evita mantener una suscripción cuando el componente deja de existir.
      takeUntilDestroyed(this.destroyRef),
      // Desbloquea el formulario al completar, fallar o cancelar la suscripción.
      finalize(() => this.processing.set(false)),
    ).subscribe({
      next: (response) => this.result.set(response),
      error: (error: unknown) => {
        if (error instanceof HttpErrorResponse) {
          if (error.status === 0) {
            this.error.set(this.texts.errors.connection);
            return;
          }

          const detail = error.error?.detail;

          if (typeof detail === 'string') {
            this.error.set(detail);
            return;
          }
        }

        this.error.set(this.texts.errors.processing);
      },
    });
  }
}