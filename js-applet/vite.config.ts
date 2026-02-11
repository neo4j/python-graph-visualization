import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import cssInjectedByJsPlugin from "vite-plugin-css-injected-by-js";
import { resolve } from "path";

// Two builds: ESM for anywidget, IIFE for HTML fallback.
// Run via BUILD_TARGET env var (see package.json scripts).
const target = process.env.BUILD_TARGET ?? "widget";

export default defineConfig({
  plugins: [
    react(),
    // For the IIFE build, inject CSS into JS so it's fully self-contained.
    // For the ESM/widget build, CSS is extracted to a file (loaded by anywidget via _css).
    ...(target === "html" ? [cssInjectedByJsPlugin()] : []),
  ],
  build: {
    lib: {
      entry: resolve(__dirname, "src/index.tsx"),
      ...(target === "widget"
        ? {
            formats: ["es"] as const,
            fileName: () => "widget.js",
          }
        : {
            name: "NVLBase",
            formats: ["iife"] as const,
            fileName: () => "base.js",
          }),
    },
    outDir: "dist",
    emptyOutDir: target === "widget", // only clean on first build
    cssCodeSplit: false,
    sourcemap: false,
    rollupOptions: {
      output: {
        // Prevent code splitting — produce a single self-contained file
        inlineDynamicImports: true,
        assetFileNames: "style.[ext]",
      },
    },
  },
});
