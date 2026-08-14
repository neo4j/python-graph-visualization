import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// HTML build: produces a single self-contained index.html with all JS and
// CSS inlined. Python injects graph data at runtime as an inert
// <script type="application/json" id="neo4j-viz-data"> block before serving.
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
