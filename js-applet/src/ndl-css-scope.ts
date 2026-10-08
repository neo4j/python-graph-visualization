/**
 * Build-time scoping for the Neo4j Design Language (NDL) stylesheet.
 *
 * NDL ships a Tailwind-style preflight with bare-element selectors (`h1`,
 * `a`, `ol,ul,menu`, `*`, `body`, …). The widget applies the whole stylesheet
 * at the host document level (as the overlay copy in `document.head` used for
 * portaled menus, and as `_css` where the host mounts it document-wide), so
 * those bare selectors reset the host page's own typography, links, lists and
 * form controls.
 *
 * This transform rewrites every selector that could match host content so it
 * only matches inside the widget, keyed off a scope attribute on the widget
 * wrapper. Class/id-scoped rules (`.ndl-*`, `.n-*`, `.cm-*`, …) are left
 * untouched: they can only match NDL content, and keeping them unscoped means
 * overlays portaled outside the wrapper (menus, tooltips) stay styled. The
 * scope is wrapped in `:where(...)` so it adds no specificity and the cascade
 * inside the widget is unchanged.
 */

export const NDL_SCOPE_ATTRIBUTE = "data-neo4j-viz-ndl";
export const NDL_SCOPE_SELECTOR = `[${NDL_SCOPE_ATTRIBUTE}]`;

// At-rules whose block contains nested style rules that must be scoped too.
const GROUP_AT_RULES = new Set(["media", "supports", "container", "layer", "scope"]);

// Selectors that describe the document root; inside the widget the wrapper
// plays that role.
const ROOT_SELECTORS = new Set(["html", "body", ":root", ":host"]);

// A class or id selector, e.g. `.ndl-btn` / `#root`. Requires a name after the
// sigil and is not preceded by an attribute/string operator, so `[href*=".com"]`
// is not mistaken for a class.
const CLASS_OR_ID_RE = /(?<![="'*~|^$])[.#][A-Za-z_-]/;

// Leading/trailing whitespace and comments, kept verbatim so a license header
// on the first selector of a list survives and never leaks into the selector.
const LEADING_RE = /^(?:\s|\/\*[\s\S]*?\*\/)*/;
const TRAILING_RE = /(?:\s|\/\*[\s\S]*?\*\/)*$/;

export function scopeNdlCss(css: string, scopeSelector: string = NDL_SCOPE_SELECTOR): string {
  return transformRules(css, scopeSelector);
}

function transformRules(text: string, scope: string): string {
  let out = "";
  let i = 0;
  const n = text.length;

  while (i < n) {
    const { prelude, index, terminator } = readPrelude(text, i);

    if (terminator === ";") {
      out += prelude + ";";
      i = index + 1;
      continue;
    }
    if (terminator !== "{") {
      out += prelude;
      break;
    }

    const end = findBlockEnd(text, index);
    const body = text.slice(index + 1, end);
    const trimmed = prelude.trim();

    if (trimmed.startsWith("@")) {
      if (GROUP_AT_RULES.has(atRuleName(trimmed))) {
        out += `${prelude}{${transformRules(body, scope)}}`;
      } else {
        out += `${prelude}{${body}}`;
      }
    } else if (isThemeRootSelector(prelude)) {
      // NDL declares its theme state (`color-scheme` and the lightningcss
      // light/dark toggles) on the document root. Hosts use the same
      // lightningcss toggles (Marimo), so leaving them on `:root` flips the
      // host's own `light-dark()` resolution. Relocate them to the widget
      // wrapper, where NDL content inherits them and the host is untouched.
      const { kept, themeState } = splitThemeState(body);
      out += `${scopeSelectorList(prelude, scope)}{${kept}}`;
      if (themeState) out += `:where(${scope}){${themeState}}`;
    } else {
      out += `${scopeSelectorList(prelude, scope)}{${body}}`;
    }

    i = end + 1;
  }

  return out;
}

/** Reads from `start` up to the next top-level `{` or `;`, skipping strings, comments and parentheses. */
function readPrelude(
  text: string,
  start: number,
): { prelude: string; index: number; terminator: "{" | ";" | "" } {
  let parens = 0;
  let i = start;
  const n = text.length;

  while (i < n) {
    const ch = text[i];
    if (ch === '"' || ch === "'") {
      i = skipString(text, i);
    } else if (ch === "/" && text[i + 1] === "*") {
      i = skipComment(text, i);
    } else if (ch === "(") {
      parens += 1;
      i += 1;
    } else if (ch === ")") {
      parens -= 1;
      i += 1;
    } else if (parens === 0 && (ch === "{" || ch === ";")) {
      return { prelude: text.slice(start, i), index: i, terminator: ch };
    } else {
      i += 1;
    }
  }

  return { prelude: text.slice(start, i), index: i, terminator: "" };
}

/** Returns the index of the `}` matching the `{` at `open`, skipping strings and comments. */
function findBlockEnd(text: string, open: number): number {
  let depth = 0;
  let i = open;
  const n = text.length;

  while (i < n) {
    const ch = text[i];
    if (ch === '"' || ch === "'") {
      i = skipString(text, i);
    } else if (ch === "/" && text[i + 1] === "*") {
      i = skipComment(text, i);
    } else if (ch === "{") {
      depth += 1;
      i += 1;
    } else if (ch === "}") {
      depth -= 1;
      if (depth === 0) return i;
      i += 1;
    } else {
      i += 1;
    }
  }

  return n;
}

function skipString(text: string, start: number): number {
  const quote = text[start];
  let i = start + 1;
  const n = text.length;
  while (i < n) {
    if (text[i] === "\\") {
      i += 2;
      continue;
    }
    if (text[i] === quote) return i + 1;
    i += 1;
  }
  return i;
}

function skipComment(text: string, start: number): number {
  const end = text.indexOf("*/", start + 2);
  return end === -1 ? text.length : end + 2;
}

function atRuleName(prelude: string): string {
  return (
    prelude
      .trim()
      .slice(1)
      .split(/[\s({;]/, 1)[0]
      ?.toLowerCase() ?? ""
  );
}

// Theme-state declarations NDL puts on the document root that collide with
// hosts using the same lightningcss/color-scheme toggles (e.g. Marimo).
const THEME_STATE_PROPS = new Set(["color-scheme", "--lightningcss-light", "--lightningcss-dark"]);

function isThemeRootSelector(prelude: string): boolean {
  return prelude.includes(":root") || prelude.includes(":host");
}

function splitThemeState(body: string): { kept: string; themeState: string } {
  const kept: string[] = [];
  const themeState: string[] = [];
  for (const declaration of splitDeclarations(body)) {
    const name = declaration.split(":", 1)[0]?.trim() ?? "";
    (THEME_STATE_PROPS.has(name) ? themeState : kept).push(declaration);
  }
  return { kept: kept.join(";"), themeState: themeState.join(";") };
}

/** Splits a declaration block on `;`, ignoring strings and parentheses. */
function splitDeclarations(body: string): string[] {
  const parts: string[] = [];
  let depth = 0;
  let start = 0;
  let i = 0;
  const n = body.length;

  while (i < n) {
    const ch = body[i];
    if (ch === '"' || ch === "'") {
      i = skipString(body, i);
      continue;
    }
    if (ch === "(" || ch === "[") depth += 1;
    else if (ch === ")" || ch === "]") depth -= 1;
    else if (ch === ";" && depth === 0) {
      parts.push(body.slice(start, i));
      start = i + 1;
    }
    i += 1;
  }
  const last = body.slice(start);
  if (last) parts.push(last);

  // Keep declarations verbatim (a meaningful trailing space in the
  // lightningcss toggle value must survive), dropping empty ones.
  return parts.filter((part) => part.trim().length > 0);
}

function scopeSelectorList(list: string, scope: string): string {
  return splitTopLevel(list, ",")
    .map((selector) => scopeSelector(selector, scope))
    .join(",");
}

function scopeSelector(selector: string, scope: string): string {
  const leading = selector.match(LEADING_RE)?.[0] ?? "";
  const trailing = selector.match(TRAILING_RE)?.[0] ?? "";
  const core = selector.slice(leading.length, selector.length - trailing.length);

  if (!core) return selector;
  // Token/theme definitions and NDL-scoped rules cannot match host content.
  if (core.includes(":root") || core.includes(":host")) return selector;
  if (CLASS_OR_ID_RE.test(core)) return selector;

  const where = `:where(${scope})`;

  if (ROOT_SELECTORS.has(core)) return `${leading}${where}${trailing}`;
  if (core === "*") return `${leading}${where}, ${where} *${trailing}`;
  // Bare pseudo-elements/classes (`::backdrop`, `:before`, `:-moz-focusring`)
  // need an explicit universal to attach to.
  if (core.startsWith(":")) return `${leading}${where} *${core}${trailing}`;
  return `${leading}${where} ${core}${trailing}`;
}

/** Splits on `separator` at nesting depth 0, ignoring strings. */
function splitTopLevel(text: string, separator: string): string[] {
  const parts: string[] = [];
  let depth = 0;
  let start = 0;
  let i = 0;
  const n = text.length;

  while (i < n) {
    const ch = text[i];
    if (ch === '"' || ch === "'") {
      i = skipString(text, i);
      continue;
    }
    if (ch === "(" || ch === "[") depth += 1;
    else if (ch === ")" || ch === "]") depth -= 1;
    else if (ch === separator && depth === 0) {
      parts.push(text.slice(start, i));
      start = i + 1;
    }
    i += 1;
  }

  parts.push(text.slice(start));
  return parts;
}
