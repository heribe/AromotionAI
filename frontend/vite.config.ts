import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // loadEnv 会按 mode 加载 .env / .env.[mode]，注入到 process.env
  const env = loadEnv(mode, process.cwd(), '')
  const backendUrl = env.VITE_BACKEND_URL ?? 'http://localhost:8000'

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src')
      }
    },
    server: {
      proxy: {
        // 把前端 /api/v1 请求转发到后端 FastAPI，同源避免 CORS
        '/api/v1': {
          target: backendUrl,
          changeOrigin: true,
        },
      },
    },
  }
})
