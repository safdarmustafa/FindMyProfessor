import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Bypass helper used only for /outreach/history, which is BOTH a React SPA page
// AND a FastAPI JSON API endpoint on the same path.
// Browser navigations (Accept: text/html) get the React SPA shell.
// fetch() calls from React components (no text/html) get proxied to FastAPI.
function bypassIfHtml(req) {
  const accept = req.headers['accept'] || '';
  if (accept.includes('text/html')) return '/index.html';
  return null;
}

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    css: true,
  },
  server: {
    port: 5173,
    proxy: {
      // ── Utility / non-conflicting API prefixes ────────────────────────────
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/api/, ''),
      },
      '/profile':     { target: 'http://localhost:8000', changeOrigin: true },
      '/cv':          { target: 'http://localhost:8000', changeOrigin: true },
      '/matching':    { target: 'http://localhost:8000', changeOrigin: true },
      '/professors':  { target: 'http://localhost:8000', changeOrigin: true },
      '/universities':{ target: 'http://localhost:8000', changeOrigin: true },

      // ── Outreach API endpoints only ───────────────────────────────────────
      // /outreach/compose/:id, /outreach/gmail-connected, /outreach/gmail-callback-error
      // are React SPA routes — they must NOT be proxied.
      '/outreach/drafts':       { target: 'http://localhost:8000', changeOrigin: true },
      '/outreach/cv-versions':  { target: 'http://localhost:8000', changeOrigin: true },

      // /outreach/history is BOTH a React SPA route AND a FastAPI JSON endpoint.
      // Use bypass: browser navigations (Accept: text/html) get the SPA shell;
      // fetch() calls from React components get proxied to FastAPI.
      '/outreach/history': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        bypass: bypassIfHtml,
      },

      // ── Gmail API endpoints only ──────────────────────────────────────────
      // /gmail/callback is called directly by Google at localhost:8000 — not proxied.
      // /outreach/gmail-connected and /outreach/gmail-callback-error are React SPA
      // routes (under /outreach, not /gmail) — they are not listed here.
      '/gmail/status':     { target: 'http://localhost:8000', changeOrigin: true },
      '/gmail/connect':    { target: 'http://localhost:8000', changeOrigin: true },
      '/gmail/disconnect': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});
