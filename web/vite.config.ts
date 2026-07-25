import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// The build lands directly inside the Python package, which is what the app
// window and PyInstaller both serve. Relative asset paths keep it working when
// the bundle is opened from anywhere.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: './',
  build: {
    outDir: '../src/sigma/web/static',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    // `npm run dev` talks to a Sigma backend started with `make api`.
    proxy: { '/api': 'http://127.0.0.1:8765' },
  },
});
