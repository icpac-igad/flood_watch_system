import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],

  // Build configuration
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        assetFileNames: (assetInfo) => {
          const extType = assetInfo.name.split('.').at(1);
          if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(extType)) {
            return `assets/images/[name][extname]`;
          }
          return `assets/[name]-[hash][extname]`;
        },
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
      },
    },
  },



  // Server configuration
  server: {
    host: '0.0.0.0',
    port: 5000,
    strictPort: false,
    allowedHosts: true,
    hmr: {
      clientPort: 443,
      protocol: 'wss'
    },
    proxy: {
      '/api/fast': {
        target: 'http://localhost:9050',
        changeOrigin: true,
        secure: false
      },
      '/api': {
        target: process.env.VITE_DJANGO_API_URL || 'http://localhost:8090',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, '/api')
      },
      '/admin': {
        target: process.env.VITE_DJANGO_API_URL || 'http://localhost:8090',
        changeOrigin: true,
        secure: false,
      },
      '/geoserver': {
        target: 'http://localhost:8093',
        changeOrigin: true,
        secure: false,
      }
    }
  },

  // Base public path
  base: '/',
  
  // Resolve aliases
  resolve: {
    alias: {
      '@': '/src',
      '@assets': '/src/assets'
    }
  }
})