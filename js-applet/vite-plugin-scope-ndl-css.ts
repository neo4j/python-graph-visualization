import type { Plugin } from "vite";

import { scopeNdlCss } from "./src/ndl-css-scope.ts";

// Scopes the NDL stylesheet to the widget wrapper at build time so it can be
// applied at the host document level (Marimo mounts the widget's `_css`
// globally) without resetting the host page. See src/ndl-css-scope.ts.
const NDL_STYLESHEET = "neo4j-ds-styles.css";

export function scopeNdlCssPlugin(): Plugin {
  return {
    name: "neo4j-viz:scope-ndl-css",
    enforce: "pre",
    transform(code, id) {
      if (!id.includes(NDL_STYLESHEET)) return;
      return { code: scopeNdlCss(code), map: null };
    },
  };
}
