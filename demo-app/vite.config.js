import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";

// One self-contained index.html: opens offline by double-click and publishes as a single page.
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  base: "./",
  build: { outDir: "../docs/app", emptyOutDir: false, chunkSizeWarningLimit: 8000, assetsInlineLimit: 100000000 },
  worker: { format: "iife" },
});
