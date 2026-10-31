import { ApplicationConfig, provideBrowserGlobalErrorListeners, provideZoneChangeDetection } from '@angular/core';
import { provideHttpClient, withFetch } from '@angular/common/http';

import { API_BASE_URL, CategoriesClient, DocumentsClient, SearchClient, TextSearchClient } from './api/api-client';
import { environment } from '../environments/environment';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideHttpClient(withFetch()),
    { provide: API_BASE_URL, useValue: environment.apiBaseUrl },
    // NSwag-generated clients (npm run api-client)
    CategoriesClient,
    SearchClient,
    TextSearchClient,
    DocumentsClient,
  ],
};
