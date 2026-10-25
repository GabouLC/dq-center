import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  // En desarrollo, /api y /health van a la API local (python -m dqc.api); DQC_API cambia su dirección.
  server: {
    port: 5173,
    proxy: {
      '/api': process.env.DQC_API ?? 'http://127.0.0.1:8000',
      '/health': process.env.DQC_API ?? 'http://127.0.0.1:8000',
    },
  },
})
