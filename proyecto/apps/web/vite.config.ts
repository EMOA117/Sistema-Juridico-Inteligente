import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [react()],
  // Evita heredar un postcss.config de carpetas superiores.
  css: { postcss: {} },
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    // core-api (FastAPI) en desarrollo local
    proxy: { '/api': 'http://localhost:8000' },
  },
});
