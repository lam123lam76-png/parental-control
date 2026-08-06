import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    // ❌ Xóa toàn bộ VitePWA khỏi đây
  ],
  build: {
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('react/') || id.includes('react-dom/')) {
              return 'vendor'
            }
            if (id.includes('lucide-react')) {
              return 'lucide'
            }
            if (id.includes('@supabase')) {
              return 'supabase'
            }
            return 'utils'
          }
        }
      }
    }
  }
})