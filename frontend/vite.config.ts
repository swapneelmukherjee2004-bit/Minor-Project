import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": new URL("./src", import.meta.url).pathname } },
  build: { rollupOptions: { output: { manualChunks: { charts: ["recharts"] } } } },
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000", "/fixtures": "http://127.0.0.1:8000" } },
});
