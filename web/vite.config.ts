import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Port 5180 is Scriptorium's claim (see RUNBOOK.md). strictPort so a
// collision fails loudly instead of silently drifting to another port.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5180,
    strictPort: true,
    proxy: {
      '/api': 'http://127.0.0.1:8012',
    },
  },
})
