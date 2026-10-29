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

  inspect(file: File): Observable<DocumentInspectionResponse> {
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<DocumentInspectionResponse>(
      this.endpoint,
      formData,
    );
  }
}