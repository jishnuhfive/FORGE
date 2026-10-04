import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { defineConfig } from 'vitest/config';

export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss()],
  server: {
    // Explicit mode: certificates are never needed for the credential-free UI lab.
    ...(mode === 'local-https'
      ? {
          https: {
            cert: readFileSync(
              resolve(import.meta.dirname, '../../.certs/localhost.pem'),
            ),
            key: readFileSync(
              resolve(import.meta.dirname, '../../.certs/localhost-key.pem'),
            ),
          },
        }
      : {}),
    proxy: {
      '/api/health': {
        target: 'http://127.0.0.1:8000',
        rewrite: () => '/health',
      },
      '/api': { target: 'http://127.0.0.1:8000' },
      '/auth': { target: 'http://127.0.0.1:8000' },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
}));
