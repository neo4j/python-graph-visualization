import anywidget from "@anywidget/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// ESM lib build for anywidget (produces widget.js + style.css).
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
      entry: ["src/graph-widget.tsx"],
      formats: ["es"],
      fileName: () => "widget.js",
    },
    rollupOptions: {
      output: {
        // anywidget serves _esm via blob URLs — relative chunk imports
        // won't resolve, so everything must be inlined into a single file.
        inlineDynamicImports: true,
        assetFileNames: "style.[ext]",
      },
    },
  },
});
