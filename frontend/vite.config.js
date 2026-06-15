import { defineConfig } from "vite";

export default defineConfig({
  root: process.cwd(),
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});
