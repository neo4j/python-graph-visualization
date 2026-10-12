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
 *
 * Structure (strings, comments, at-rules, selector lists) is parsed by postcss;
 * only the scoping policy below is ours.
 */

import postcss, { type Declaration, type Rule } from "postcss";

export const NDL_SCOPE_ATTRIBUTE = "data-neo4j-viz-ndl";
export const NDL_SCOPE_SELECTOR = `[${NDL_SCOPE_ATTRIBUTE}]`;

// Selectors that describe the document root; inside the widget the wrapper
// plays that role.
const ROOT_SELECTORS = new Set(["html", "body", ":root", ":host"]);

// A class or id selector, e.g. `.ndl-btn` / `#root`. Requires a name after the
// sigil and is not preceded by an attribute/string operator, so `[href*=".com"]`
// is not mistaken for a class.
const CLASS_OR_ID_RE = /(?<![="'*~|^$])[.#][A-Za-z_-]/;

// Theme-state declarations NDL puts on the document root that collide with
// hosts using the same lightningcss/color-scheme toggles (e.g. Marimo).
const THEME_STATE_PROPS = new Set(["color-scheme", "--lightningcss-light", "--lightningcss-dark"]);

export function scopeNdlCss(css: string, scope: string = NDL_SCOPE_SELECTOR): string {
  const root = postcss.parse(css);
  const where = `:where(${scope})`;

  root.walkRules((rule) => {
    // `@keyframes` step selectors (`from`, `to`, `50%`) are rules too.
    if (isInsideKeyframes(rule)) return;
    rule.selector = rule.selectors.map((selector) => scopeSelector(selector, where)).join(",");
  });

  // Separate pass so the relocated theme-state rule (added below) is not scoped.
  root.walkRules((rule) => {
    if (isInsideKeyframes(rule)) return;
    if (rule.selectors.some(isThemeRootSelector)) relocateThemeState(rule, where);
  });

  return root.toString();
}

/**
 * NDL declares its theme state (`color-scheme` and the lightningcss light/dark
 * toggles) on the document root. Hosts use the same lightningcss toggles
 * (Marimo), so leaving them on `:root` flips the host's own `light-dark()`
 * resolution. Move them to the widget wrapper, where NDL content inherits them
 * and the host is untouched.
 */
function relocateThemeState(rule: Rule, where: string): void {
  const moved: Declaration[] = [];
  rule.walkDecls((decl) => {
    if (THEME_STATE_PROPS.has(decl.prop)) moved.push(decl);
  });
  if (moved.length === 0) return;

  const relocated = postcss.rule({ selector: where });
  relocated.raws.before = "";
  for (const decl of moved) {
    decl.remove();
    relocated.append(decl);
  }
  rule.parent?.insertAfter(rule, relocated);
}

function scopeSelector(selector: string, where: string): string {
  if (!selector) return selector;
  // Token/theme definitions and NDL-scoped rules cannot match host content.
  if (isThemeRootSelector(selector)) return selector;
  if (CLASS_OR_ID_RE.test(selector)) return selector;

  if (ROOT_SELECTORS.has(selector)) return where;
  if (selector === "*") return `${where}, ${where} *`;
  // Bare pseudo-elements/classes (`::backdrop`, `:before`, `:-moz-focusring`)
  // need an explicit universal to attach to.
  if (selector.startsWith(":")) return `${where} *${selector}`;
  return `${where} ${selector}`;
}

function isThemeRootSelector(selector: string): boolean {
  return selector.includes(":root") || selector.includes(":host");
}

function isInsideKeyframes(rule: Rule): boolean {
  const parent = rule.parent;
  return parent?.type === "atrule" && parent.name.toLowerCase().endsWith("keyframes");
}
