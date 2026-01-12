import { defineConfig } from 'vite'
import path from 'path'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // --- THIS IS THE CRITICAL PART FOR PI ACCESS ---
  server: {
    host: true,       // Listen on all IPs (allows network access)
    port: 5173,       // Lock the port
    strictPort: true, // Don't switch ports if busy
  }
})