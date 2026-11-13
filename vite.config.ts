
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { fileURLToPath } from "node:url";

const projectDir = path.dirname(fileURLToPath(import.meta.url));
const srcDir = path.resolve(projectDir, "src");

export default defineConfig({
  configFile: path.resolve(projectDir, "vite.config.ts"),
  plugins: [react()],
  root: srcDir,
  base: "./",
  build: {
    outDir: path.resolve(projectDir, "dist-renderer"),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    strictPort: true,
  },
  resolve: {
    alias: {
      "@": srcDir,
    },
  },
});
