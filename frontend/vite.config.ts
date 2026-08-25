import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  legacy: {
    skipWebSocketTokenCheck: true,
  },
  plugins: [react()],
  optimizeDeps: {
    // Pre-bundle these so the dependency optimizer does not re-run (and change
    // its ?v= cache-busting hash) on routine edits, which otherwise leaves the
    // browser holding stale /node_modules/.vite/deps URLs behind a blank screen.
    //
    // noDiscovery prevents the optimizer from scanning for new deps at runtime,
    // which would trigger a re-run and invalidate every cached module URL.
    // If a new dependency causes an error, add it to the include list below.
    noDiscovery: true,
    include: [
      'react',
      'react-dom',
      'react-dom/client',
      'react-router-dom',
      '@tanstack/react-query',
      'axios',
      'zod',
      'react-hook-form',
      '@hookform/resolvers',
      '@hookform/resolvers/zod',
      'lucide-react',
      '@twilio/voice-sdk',
    ],
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: false,
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: false,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      },
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 4173,
    allowedHosts: true,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: true,
  },
})
