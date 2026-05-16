import path from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000/api/v1'

export default defineConfig(({ mode }) => {
  const envDir = path.resolve(__dirname, '..')
  const env = loadEnv(mode, envDir, '')
  const apiBaseUrl = env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
  const apiTarget = new URL(apiBaseUrl).origin

  return {
    envDir,
    plugins: [react()],
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
