/// <reference types="vitest" />
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  // Load env file from the parent directory as specified by envDir.
  // Empty prefix loads all keys (not only VITE_*), so BACKEND_URL is available here at config time.
  const env = loadEnv(mode, '../', '');
  
  return {
    envDir: '..',
    plugins: [react()],
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: env.BACKEND_URL || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: [],
    }
  };
});

