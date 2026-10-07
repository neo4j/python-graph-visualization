import fs from "node:fs";
import path from "node:path";
import type { Plugin, ResolvedConfig } from "vite";

// NVL ships its layout web workers as separate chunks (e.g.
// `CoseBilkentLayout.worker-<hash>.js`), but the widget forces
// `disableWebWorkers: true`, so they are never fetched. Vite still emits them as
// build assets (and `emptyOutDir: false` lets stale ones accumulate), so drop them
// after each build to keep the resources directory (and wheel) free of dead weight.
const WORKER_FILE_RE = /\.worker-[A-Za-z0-9_-]+\.js$/;

export function cleanWorkerChunks(): Plugin {
  let outDir = "";

  return {
    name: "neo4j-viz:clean-worker-chunks",
    apply: "build",
    configResolved(config: ResolvedConfig) {
      outDir = path.resolve(config.root, config.build.outDir);
    },
    closeBundle() {
      if (!outDir) return;
      for (const dir of [outDir, path.join(outDir, "assets")]) {
        if (!fs.existsSync(dir)) continue;
        for (const entry of fs.readdirSync(dir)) {
          if (WORKER_FILE_RE.test(entry)) {
            fs.rmSync(path.join(dir, entry), { force: true });
          }
        }
      }
    },
  };
}
