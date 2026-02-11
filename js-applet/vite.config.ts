import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Single ESM build for anywidget.
// The same widget.js is used by both the anywidget Jupyter path
// and the standalone HTML fallback (via a lightweight model shim).
export default defineConfig({
  plugins: [react()],
  define: {
    // React/NDL reference process.env.NODE_ENV at runtime
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  build: {
    outDir: "../python-wrapper/src/neo4j_viz/resources/nvl_entrypoint",
    emptyOutDir: false,
    lib: {
      entry: ["src/index.tsx"],
      formats: ["es"],
      fileName: () => "widget.js",
    },
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        // Single file — anywidget loads _esm as a blob, so relative imports won't resolve
        inlineDynamicImports: true,
        assetFileNames: "style.[ext]",
      },
    },
  },
});
