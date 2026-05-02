import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      // 彻底屏蔽 VR/AR/3D 模块，避免加载 A-Frame 相关依赖
      '3d-force-graph-vr': path.resolve(__dirname, './src/stubs/empty.js'),
      '3d-force-graph-ar': path.resolve(__dirname, './src/stubs/empty.js'),
      '3d-force-graph': path.resolve(__dirname, './src/stubs/empty.js'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    exclude: ['3d-force-graph-vr', '3d-force-graph-ar', '3d-force-graph'],
  },
})
