"""Guard that the shipped NDL stylesheet is scoped to the widget wrapper.

The stylesheet is shipped as the widget's ``_css`` and applied at the host
document level (as the overlay copy in document.head), so any bare element
selector in it (``h1``, ``a``, ``*``, …) would reset the host page, and any
theme-state declaration on the document root (``color-scheme``,
``--lightningcss-*``) would flip the host's own light/dark resolution. The build
scopes/relocates both; this test fails if an unscoped selector or a root-level
theme-state declaration ever ships again (see GDS-440).
"""

from __future__ import annotations

import re
from pathlib import Path

import neo4j_viz

STYLE_CSS = Path(neo4j_viz.__file__).parent / "resources" / "nvl_entrypoint" / "style.css"

# A class or id selector, e.g. `.ndl-btn`. Requires a name after the sigil and
# is not preceded by an attribute/string operator, so `[href*=".com"]` is not
# mistaken for a class.
_CLASS_OR_ID = re.compile(r"""(?<![="'*~|^$])[.#][A-Za-z_-]""")
_THEME_STATE_PROPS = ("color-scheme", "--lightningcss-light", "--lightningcss-dark")


def _top_level_rules(css: str) -> list[tuple[str, str]]:
    """``(selector_list, declaration_block)`` for every style rule at the top level."""
    rules: list[tuple[str, str]] = []
    depth = 0
    buf = ""
    i = 0
    n = len(css)
    while i < n:
        ch = css[i]
        if ch in "\"'":
            quote = ch
            buf += ch
            i += 1
            while i < n and css[i] != quote:
                if css[i] == "\\":
                    buf += css[i]
                    i += 1
                buf += css[i]
                i += 1
            if i < n:
                buf += css[i]
                i += 1
            continue
        buf += ch
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                selector, _, body = buf.partition("{")
                body = body.rstrip("}")
                if not selector.strip().startswith("@"):
                    rules.append((selector.strip(), body))
                buf = ""
        i += 1
    return rules


def _split_top_level(selector_list: str) -> list[str]:
    """Split a selector list on commas outside parentheses/brackets."""
    parts: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(selector_list):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(selector_list[start:i])
            start = i + 1
    parts.append(selector_list[start:])
    return parts


def _is_root_selector(selector: str) -> bool:
    return selector in ("html", "body") or ":root" in selector or ":host" in selector


def test_shipped_style_css_has_no_unscoped_bare_selectors() -> None:
    css = STYLE_CSS.read_text()

    offenders = []
    for selector_list, _ in _top_level_rules(css):
        for selector in _split_top_level(selector_list):
            core = selector.strip()
            if not core:
                continue
            if ":root" in core or ":host" in core:
                continue
            if _CLASS_OR_ID.search(core):
                continue
            if "data-neo4j-viz-ndl" in core:
                continue
            offenders.append(core)

    assert offenders == [], f"unscoped bare-element selectors leaked into style.css: {offenders}"


def test_shipped_style_css_has_no_root_theme_state() -> None:
    css = STYLE_CSS.read_text()

    offenders = []
    for selector_list, body in _top_level_rules(css):
        if not any(_is_root_selector(s.strip()) for s in _split_top_level(selector_list)):
            continue
        for prop in _THEME_STATE_PROPS:
            if re.search(rf"(?:^|;)\s*{re.escape(prop)}\s*:", body):
                offenders.append(f"{selector_list.strip()} {{{prop}}}")

    assert offenders == [], f"theme state leaked onto the document root in style.css: {offenders}"
