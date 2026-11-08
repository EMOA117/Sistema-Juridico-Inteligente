// Pruebas de navegador de punta a punta (portadas de feature/modulo-ODR). Requieren el entorno local levantado:
// API en :8000, tareas en segundo plano, Mailpit en :8025 y `npm run dev`. Ver infrastructure/local/README.md.
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 120_000,
  expect: { timeout: 15_000 },
  workers: 1,
  use: {
    baseURL: process.env.WEB_URL ?? 'http://localhost:5173',
    // Usa el Chrome instalado para no descargar navegadores; PLAYWRIGHT_CHANNEL='' usa el Chromium de Playwright.
    channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  reporter: 'list',
});
