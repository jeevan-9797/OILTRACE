import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  const backendTarget = process.env.VITE_API_BASE_URL || 'https://oil-trace.onrender.com';
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      hmr: process.env.DISABLE_HMR !== 'true',
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          headers: {
            Origin: 'https://oil-trace-two.vercel.app',
          },
        },
        '/health': {
          target: backendTarget,
          changeOrigin: true,
          headers: {
            Origin: 'https://oil-trace-two.vercel.app',
          },
        },
      },
    },
    preview: {
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          headers: {
            Origin: 'https://oil-trace-two.vercel.app',
          },
        },
        '/health': {
          target: backendTarget,
          changeOrigin: true,
          headers: {
            Origin: 'https://oil-trace-two.vercel.app',
          },
        },
      },
    },
  };
});
