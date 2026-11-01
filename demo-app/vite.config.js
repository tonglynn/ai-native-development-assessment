import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Multi-file build: pages, Monaco and the Python runtime load only when a view needs them.
// Serve docs/app over HTTP (python -m http.server -d docs/app) — browsers do not load WebAssembly from file://.
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: { outDir: "../docs/app", emptyOutDir: true, chunkSizeWarningLimit: 8000 },
  worker: { format: "iife" },
});
