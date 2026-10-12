"""Guard that the shipped NDL stylesheet is scoped to the widget wrapper.

The stylesheet is shipped as the widget's ``_css`` and applied at the host
document level (as the overlay copy in document.head), so a bare element
selector in it (``h1``, ``a``, ``*``, …) would reset the host page, and a
theme-state declaration on the document root (``color-scheme``,
``--lightningcss-*``) would flip the host's own light/dark resolution. The build
scopes/relocates both; this test is a cheap tripwire over the shipped,
minified file.

It is deliberately keyed to the known preflight selectors/properties rather than
being a full CSS parser: it can miss an unscoped selector of a shape it does not
know (the generic build transform and the browser end-to-end tests cover those),
but it runs everywhere without a browser.
"""

from __future__ import annotations

import re
from pathlib import Path

import neo4j_viz

STYLE_CSS = Path(neo4j_viz.__file__).parent / "resources" / "nvl_entrypoint" / "style.css"

# A bare element/universal selector at a rule boundary (start of the sheet, or
# after a rule/selector-list separator) immediately followed by the next
# selector or the declaration block. Scoped selectors are prefixed with
# `:where([data-neo4j-viz-ndl])`, so their bare names are not at a boundary.
_BARE_SELECTOR = re.compile(
    r"(?:^|[},])\s*"
    r"(?:h[1-6]|a|b|i|p|q|s|u|em|strong|small|sub|sup|pre|code|kbd|samp|abbr|"
    r"body|html|ol|ul|menu|li|dl|dt|dd|table|button|input|select|textarea|"
    r"optgroup|fieldset|legend|summary|dialog|hr|blockquote|figure|figcaption|"
    r"img|svg|video|canvas|audio|iframe|embed|object|\*)"
    r"\s*(?:,|\{)"
)

_THEME_STATE_PROPS = ("color-scheme", "--lightningcss-light", "--lightningcss-dark")
_ROOT_SELECTOR = re.compile(r":root|:host")


def test_shipped_style_css_has_no_unscoped_bare_selectors() -> None:
    css = STYLE_CSS.read_text()

    offenders = [match.group(0).strip() for match in _BARE_SELECTOR.finditer(css)]

    assert offenders == [], f"unscoped bare-element selectors leaked into style.css: {offenders}"


def test_shipped_style_css_has_no_root_theme_state() -> None:
    css = STYLE_CSS.read_text()

    offenders = []
    # The root token blocks are top-level and brace-free inside their bodies, so
    # a crude rule split is enough.
    for match in re.finditer(r"([^{}]*)\{([^}]*)\}", css):
        selector, body = match.group(1), match.group(2)
        if not _ROOT_SELECTOR.search(selector):
            continue
        for prop in _THEME_STATE_PROPS:
            if re.search(rf"(?:^|;)\s*{re.escape(prop)}\s*:", body):
                offenders.append(f"{selector.strip()} {{{prop}}}")

    assert offenders == [], f"theme state leaked onto the document root in style.css: {offenders}"
