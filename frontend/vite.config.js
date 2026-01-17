import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  root: process.cwd().includes('frontend') ? '.' : 'frontend',
  base: process.env.ELECTRON === 'true' ? './' : '/shadow_writing_agent/',
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    minify: 'esbuild', // 恢复默认压缩设置
    sourcemap: false, // 生产环境不生成源码映射
    esbuild: {
      drop: ['console', 'debugger'], // 移除调试代码
    },
  },
  server: {
    port: 5173,
    proxy: {
      // 代理API请求到后端
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      // WebSocket代理
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  }
})
