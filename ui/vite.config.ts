import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// One self-contained HTML file, written into the Python package so it ships in the wheel.
// The server serves it as ui://statcan/canvas.html and, with a payload embedded, as the
// standalone page for render_view links.
export default defineConfig({
  plugins: [viteSingleFile()],
  build: {
    outDir: "../src/ui_views",
    emptyOutDir: false,
    target: "es2022",
    rollupOptions: { input: "canvas.html" },
  },
});
