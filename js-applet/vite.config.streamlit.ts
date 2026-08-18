import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Streamlit build: produces an ES module (graph.js + style.css) shipped as package
// data and passed inline as the `js`/`css` of an st.components.v2.component (see
// python-wrapper/src/neo4j_viz/streamlit.py). The module's default export is the v2
// mount function in src/streamlit-entrypoint.ts.
export default defineConfig({
  plugins: [react()],
  define: {
    // React reads process.env.NODE_ENV at runtime.
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  build: {
    outDir: "../python-wrapper/src/neo4j_viz/resources/streamlit_v2",
    emptyOutDir: true,
    lib: {
      entry: ["src/streamlit-entrypoint.ts"],
      formats: ["es"],
      fileName: () => "graph.js",
    },
    rollupOptions: {
      output: {
        // Bundle everything into a single graph.js + style.css.
        // (codeSplitting:false replaces the deprecated inlineDynamicImports:true)
        codeSplitting: false,
        assetFileNames: "style.[ext]",
      },
    },
  },
});
