import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// HTML build: produces a single self-contained HTML file (template.html)
// with all JS and CSS inlined. Python injects graph data at runtime via
// window.__NEO4J_VIZ_DATA__ before serving it.
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  build: {
    outDir: "../python-wrapper/src/neo4j_viz/resources/nvl_entrypoint",
    emptyOutDir: false,
  },
});
