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
    // LOCAL: use '127.0.0.1'
    // STAGING: use '0.0.0.0'
    host: '127.0.0.1',
    port: 8094,
    proxy: {
      '/api': {
        // LOCAL: use 'http://127.0.0.1:8090'
        // STAGING: use 'http://10.10.1.13:8090'
        target: 'http://127.0.0.1:8090',
        changeOrigin: true,
        secure: false,
      },
      '/geoserver': {
        // LOCAL: use 'http://127.0.0.1:8093'
        // STAGING: use 'http://10.10.1.13:8093'
        target: 'http://127.0.0.1:8093',
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