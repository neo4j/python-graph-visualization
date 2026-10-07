import anywidget from "@anywidget/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

import { cleanWorkerChunks } from "./vite-plugin-clean-worker-chunks.ts";

// ESM lib build for anywidget (produces widget.js + style.css).
// Dev server: `yarn dev` starts Vite with HMR via @anywidget/vite.
// Python widget points _esm at http://localhost:5173/src/index.tsx?anywidget
export default defineConfig({
  plugins: [react(), anywidget(), cleanWorkerChunks()],
  define: {
    // React reference process.env.NODE_ENV at runtime
    "process.env.NODE_ENV": JSON.stringify("production"),
    // Transitive UMD deps (lodash, classnames, layout-base, cose-base, RBush, ...)
    // call the AMD `define()` when a loader is present. Hosts that load requirejs
    // (PyCharm, VS Code) then throw "Mismatched anonymous define() module" while
    // evaluating the widget module, which aborts it (anywidget's 2s init timeout
    // fires -> "Failed to initialize model"). Neutralize the AMD branch.
    "define.amd": "undefined",
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
        // Required to help bundle the widget.js and style.css into a single file
        // (codeSplitting:false replaces the deprecated inlineDynamicImports:true)
        codeSplitting: false,
        assetFileNames: "style.[ext]",
      },
    },
  },
});
