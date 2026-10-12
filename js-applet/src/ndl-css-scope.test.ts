import { describe, expect, it } from "vitest";

import { NDL_SCOPE_SELECTOR, scopeNdlCss } from "./ndl-css-scope";

const S = NDL_SCOPE_SELECTOR;
const W = `:where(${S})`;

describe("scopeNdlCss", () => {
  it("scopes bare element selectors under the widget wrapper", () => {
    expect(scopeNdlCss("h1,h2,h3,h4,h5,h6{font-size:inherit}")).toBe(
      `${W} h1,${W} h2,${W} h3,${W} h4,${W} h5,${W} h6{font-size:inherit}`,
    );
  });

  it("keeps NDL class rules untouched", () => {
    expect(scopeNdlCss(".ndl-btn{color:red}")).toBe(".ndl-btn{color:red}");
    expect(scopeNdlCss(".n-display{font-size:30px}")).toBe(".n-display{font-size:30px}");
    expect(scopeNdlCss(".cm-editor .cm-button{cursor:pointer}")).toBe(
      ".cm-editor .cm-button{cursor:pointer}",
    );
  });

  it("scopes only the bare-element part of a mixed selector list", () => {
    expect(scopeNdlCss("h1,.n-display{font-size:30px}")).toBe(`${W} h1,.n-display{font-size:30px}`);
  });

  it("maps document roots onto the wrapper", () => {
    expect(scopeNdlCss("body{margin:0}")).toBe(`${W}{margin:0}`);
    expect(scopeNdlCss("html,:host{line-height:1.5}")).toBe(`${W},:host{line-height:1.5}`);
  });

  it("expands the universal selector to cover the wrapper and its descendants", () => {
    expect(scopeNdlCss("*,:before,:after{box-sizing:border-box}")).toBe(
      `${W}, ${W} *,${W} *:before,${W} *:after{box-sizing:border-box}`,
    );
  });

  it("attaches bare pseudo selectors to a descendant universal", () => {
    expect(scopeNdlCss("::backdrop{color:red}")).toBe(`${W} *::backdrop{color:red}`);
    expect(scopeNdlCss(":focus-visible{outline:auto}")).toBe(`${W} *:focus-visible{outline:auto}`);
    expect(scopeNdlCss("input::-moz-placeholder{opacity:1}")).toBe(
      `${W} input::-moz-placeholder{opacity:1}`,
    );
  });

  it("scopes attribute-only selectors", () => {
    expect(scopeNdlCss("button,[role=button]{cursor:pointer}")).toBe(
      `${W} button,${W} [role=button]{cursor:pointer}`,
    );
  });

  it("leaves design-token definitions untouched", () => {
    expect(scopeNdlCss(":where(:root,:host){--theme-color-primary:#fff}")).toBe(
      ":where(:root,:host){--theme-color-primary:#fff}",
    );
  });

  it("recurses into group at-rules but not into declaration at-rules", () => {
    expect(scopeNdlCss("@media (min-width:1px){h1{color:red}}")).toBe(
      `@media (min-width:1px){${W} h1{color:red}}`,
    );
    expect(scopeNdlCss("@font-face{font-family:X;src:url(x.woff2)}")).toBe(
      "@font-face{font-family:X;src:url(x.woff2)}",
    );
    expect(scopeNdlCss("@keyframes spin{from{opacity:0}to{opacity:1}}")).toBe(
      "@keyframes spin{from{opacity:0}to{opacity:1}}",
    );
    expect(scopeNdlCss("@property --x{syntax:'<color>'}")).toBe("@property --x{syntax:'<color>'}");
  });

  it("preserves specificity by zeroing the scope with :where", () => {
    expect(scopeNdlCss("a{color:inherit}")).toBe(`${W} a{color:inherit}`);
    expect(scopeNdlCss("a{color:inherit}")).not.toContain(`${S} a`);
  });

  it("does not split commas inside :where()/:not() or strings", () => {
    expect(scopeNdlCss(":where(:root,:host){--x:1}")).toBe(":where(:root,:host){--x:1}");
    expect(scopeNdlCss('a[href="x,y"]{color:red}')).toBe(`${W} a[href="x,y"]{color:red}`);
  });

  it("does not confuse attribute values with class selectors", () => {
    expect(scopeNdlCss("input:where([type=button]){border:0}")).toBe(
      `${W} input:where([type=button]){border:0}`,
    );
  });

  it("keeps leading comments and does not treat them as class selectors", () => {
    expect(
      scopeNdlCss(
        "/* ! tailwindcss | https://tailwindcss.com */\n*,\n::before{box-sizing:border-box}",
      ),
    ).toBe(
      `/* ! tailwindcss | https://tailwindcss.com */\n${W}, ${W} *,${W} *::before{box-sizing:border-box}`,
    );
  });

  it("relocates theme-state declarations from the document root to the wrapper", () => {
    expect(
      scopeNdlCss(
        ":where(:root,:host){--theme-x:1;color-scheme:light;--lightningcss-light:initial;--lightningcss-dark: }",
      ),
    ).toBe(
      `:where(:root,:host){--theme-x:1}:where(${S}){color-scheme:light;--lightningcss-light:initial;--lightningcss-dark: }`,
    );
  });

  it("does not relocate theme state from class-scoped theme rules", () => {
    expect(scopeNdlCss(".ndl-theme-dark{color-scheme:dark;--lightningcss-dark:initial}")).toBe(
      ".ndl-theme-dark{color-scheme:dark;--lightningcss-dark:initial}",
    );
  });
});
