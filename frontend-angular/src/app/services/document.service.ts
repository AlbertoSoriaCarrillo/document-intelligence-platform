import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { DocumentInspectionResponse } from '../models/document.model';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class DocumentService {
  private readonly http = inject(HttpClient);

  private readonly endpoint =
    `${environment.apiUrl}/api/documents/inspect`;

  /**
   * Envía el archivo en el campo multipart esperado por FastAPI.
   * La petición se ejecuta al suscribirse; el componente gestiona carga y errores.
   * El tipo de respuesta describe el contrato, no valida el JSON en ejecución.
   */
  inspect(file: File): Observable<DocumentInspectionResponse> {
    const formData = new FormData();
    formData.append('file', file);

    // El navegador genera Content-Type y el boundary; no deben fijarse manualmente.
    return this.http.post<DocumentInspectionResponse>(
      this.endpoint,
      formData,
    );
  }
}