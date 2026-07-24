import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// data/ lives outside src/ — allow Vite's dev server to read the curated
// drug records from the repo root (see docs/data-pipeline.md).
export default defineConfig({
  plugins: [react()],
  server: {
    fs: { allow: [".."] },
  },
});
