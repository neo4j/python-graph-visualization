// @neo4j-ndl/react ships bundler-style ESM: relative imports without file
// extensions. Node's ESM resolver requires the extension, so retry with it.
export async function resolve(specifier, context, nextResolve) {
  try {
    return await nextResolve(specifier, context);
  } catch (error) {
    if (specifier.startsWith(".")) {
      for (const candidate of [`${specifier}.js`, `${specifier}/index.js`]) {
        try {
          return await nextResolve(candidate, context);
        } catch {
          // Try the next candidate.
        }
      }
    }
    throw error;
  }
}
