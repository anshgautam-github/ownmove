import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Pinned rather than left to Vite's default auto-increment: the backend's
  // CORS_ORIGINS (backend/.env) only allows http://localhost:5173 and
  // http://127.0.0.1:5173. If port 5173 is already taken by another process,
  // Vite silently starts on 5174/5175/... instead, which makes every request
  // fail CORS preflight with a 400 "Disallowed CORS origin" — the browser
  // shows "could not reach the server" and the backend logs look completely
  // unrelated to the real cause. `strictPort: true` fails loudly instead of
  // silently switching, so this class of bug surfaces immediately.
  server: {
    port: 5173,
    strictPort: true,
  },
})
