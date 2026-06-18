import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  // base: '' keeps absolute paths in the build (works for the EXE default port).
  // base: './' emits relative paths so the bundle also works when reverse-proxied
  // under a sub-path. We use './' here for maximum flexibility.
  base: './',
  cacheDir: '../.cache/vite',
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
})
