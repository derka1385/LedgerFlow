/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: the UI proxies /api to the backend. Default target is the DEV MOCK API;
// point LEDGERFLOW_API at Codex's backend when it exists (same origin in production).
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: { "/api": { target: process.env.LEDGERFLOW_API ?? "http://127.0.0.1:8787", changeOrigin: false } },
  },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
