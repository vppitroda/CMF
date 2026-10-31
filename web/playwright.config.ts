import { defineConfig } from '@playwright/test';

// Smoke test of the four-step flow against the real API + ingested DB (docker compose up -d; ingest first).
export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  use: { baseURL: 'http://localhost:4200', viewport: { width: 1500, height: 950 } },
  webServer: [
    {
      command: 'dotnet run --project ../api/Docsearch.Api --urls http://localhost:5013',
      url: 'http://localhost:5013/api/categories',
      reuseExistingServer: true,
      timeout: 120_000,
    },
    { command: 'npm start', url: 'http://localhost:4200', reuseExistingServer: true, timeout: 120_000 },
  ],
});
