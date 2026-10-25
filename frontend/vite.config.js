import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Запросы фронта идут на относительный /api — dev-сервер проксирует их на бэкенд.
// API_TARGET переопределяет адрес бэкенда (например, имя сервиса в Docker).
const apiTarget = process.env.API_TARGET ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': { target: apiTarget, changeOrigin: true } },
  },
  preview: {
    port: 4173,
    proxy: { '/api': { target: apiTarget, changeOrigin: true } },
  },
});
