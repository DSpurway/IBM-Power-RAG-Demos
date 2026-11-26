import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// Backend for local development. Use `npm run mock` for a canned backend, or point
// this at a real rag-backend:  RAG_BACKEND_URL=http://host:8401 npm run dev
const backend = process.env.RAG_BACKEND_URL || 'http://localhost:8401';

export default defineConfig(() => ({
  build: {
    outDir: 'build',
    cssMinify: 'esbuild',
  },
  css: {
    preprocessorOptions: {
      scss: {
        silenceDeprecations: ['if-function'],
      },
    },
  },
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': { target: backend, changeOrigin: true },
      '/health': { target: backend, changeOrigin: true },
    },
  },
}));
