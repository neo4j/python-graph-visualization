import anywidget from "@anywidget/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Single ESM build for anywidget.
// The same widget.js is used by both the anywidget Jupyter path
// and the standalone HTML fallback (via a lightweight model shim).
//
// Dev server: `yarn dev` starts Vite with HMR via @anywidget/vite.
// Python widget points _esm at http://localhost:5173/src/index.tsx?anywidget
export default defineConfig({
  plugins: [react(), anywidget()],
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
