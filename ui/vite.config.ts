import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// One self-contained HTML file per view (MCP Apps hosts render it in a sandboxed
// iframe with a no-network CSP), written into the Python package so it ships in the wheel.
export default defineConfig({
  plugins: [viteSingleFile()],
  build: {
    outDir: "../src/ui_views",
    emptyOutDir: false,
    target: "es2022",
    rollupOptions: { input: "series-view.html" },
  },
});
