"""Streamlit integration for :class:`~neo4j_viz.widget.GraphWidget`.

Streamlit doesn't speak the Jupyter/anywidget comm protocol, so a ``GraphWidget``
can't be embedded the way it is in a notebook.

This module bridges the same React frontend (reused from the notebook widget) as a
`Streamlit Components v2` component, using the widget's
own ``get_state``/``set_state`` -- which *do* honour ``to_json``/``from_json`` -- for
serialization. Selection and option changes made in the browser flow back to the
Python ``GraphWidget`` on the next rerun.

Requires the ``streamlit`` optional dependency: ``pip install neo4j-viz[streamlit]``.

Example
-------
>>> import streamlit as st
>>> from neo4j_viz import Node, Relationship, VisualizationGraph
>>> from neo4j_viz.streamlit import render_widget
>>>
>>> vg = VisualizationGraph(nodes=[Node(id="0"), Node(id="1")], relationships=[])
>>> widget = render_widget(vg.render_widget(), key="graph")
>>> st.write("Selected nodes:", widget.selected.nodeIds)
"""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from typing import Any, Literal

try:
    import streamlit as st
    from streamlit.components.v2 import component
    from streamlit.components.v2.types import ComponentRenderer
except ImportError as exc:
    raise ImportError(
        "neo4j_viz.streamlit requires the optional 'streamlit' dependency "
        "(streamlit>=1.58, for the Components v2 API). "
        "Install it with: pip install 'neo4j-viz[streamlit]'"
    ) from exc

from .widget import GraphWidget

# Traits pushed to the frontend on every render. Mirrors the sync traits that the
# JS component reads (see js-applet/src/graph-widget.tsx). They are serialized via
# ``GraphWidget.get_state()``, which applies each trait's ``to_json`` -- the step
# the unmaintained streamlit-anywidget bridge skips.
_SEND_KEYS = ("nodes", "relationships", "options", "width", "height", "theme", "selected", "legend")

# Traits the frontend may write back to Python. Must stay in sync with
# ``WRITABLE_KEYS`` in js-applet/src/streamlit-entrypoint.ts.
_RECEIVE_KEYS = ("selected", "options")


@lru_cache(maxsize=1)
def _component() -> ComponentRenderer:
    """Declare (once per process) the Streamlit v2 component.

    The frontend is the self-contained ES module produced by the ``build:streamlit``
    step and shipped as package data. It is passed inline (rather than served from an
    ``asset_dir``, which requires a package manifest that is unreliable for installed
    wheels); Streamlit's ForwardMsg cache dedupes the payload across reruns.
    """
    resources = files("neo4j_viz") / "resources" / "streamlit_v2"
    # Prepend a marker comment: Streamlit classifies a string as a file path (rather
    # than inline content) when it has no newline and contains "/". A minified,
    # single-line stylesheet would be misread as a path, so the leading comment
    # guarantees an internal newline and thus inline classification.
    js = "// neo4j-viz streamlit component\n" + (resources / "graph.js").read_text(encoding="utf-8")
    css = "/* neo4j-viz streamlit component */\n" + (resources / "style.css").read_text(encoding="utf-8")
    return component("neo4j_viz_graph", js=js, css=css)


def _session_state() -> Any:
    """Indirection over ``st.session_state`` so it can be stubbed in tests."""
    return st.session_state


def _persisted_state(key: str | None) -> dict[str, Any]:
    """Return the component's persisted state (``selected``/``options`` the user last
    set in the browser), keyed by ``key``. Empty before the first interaction or when
    no ``key`` is given."""
    if key is None:
        return {}
    try:
        session_state = _session_state()
        if key in session_state:
            value = session_state[key]
            if isinstance(value, dict):
                return value
    except Exception:
        # Reading widget state can fail outside a script run; fall back to empty.
        pass
    return {}


def _component_height(height: Any) -> int | Literal["content"]:
    """Map the widget's CSS height (e.g. ``"600px"``) to a v2 ``height`` argument.

    Pixel heights become an int so the component is sized/scrollable; anything else
    (e.g. ``"100%"``) falls back to ``"content"`` so the wrapper hugs the inner graph.
    """
    if isinstance(height, str) and height.endswith("px"):
        try:
            return int(float(height[:-2]))
        except ValueError:
            pass
    return "content"


def render_widget(widget: GraphWidget, *, key: str | None = None) -> GraphWidget:
    """Render a :class:`~neo4j_viz.widget.GraphWidget` in a Streamlit app with two-way sync.

    Displays the same interactive visualization as the widget does in a notebook
    (pan/zoom, selection, layout switching, legend, side panel). Changes made in the
    browser to the selection and render options are synced back into the returned
    ``GraphWidget`` on the next Streamlit rerun, so they can be read from Python
    (e.g. ``widget.selected``) and reacted to.

    Parameters
    ----------
    widget:
        A :class:`~neo4j_viz.widget.GraphWidget`, as returned by
        :meth:`VisualizationGraph.render_widget`.
    key:
        A stable, unique Streamlit widget key. Strongly recommended: it lets
        Streamlit persist the widget's ``selected``/``options`` state across reruns,
        so interactions like changing the layout or selecting nodes are not reset on
        the next rerun. Required when rendering more than one graph in the same app.

    Returns
    -------
    The given :class:`~neo4j_viz.widget.GraphWidget`, with ``selected`` and
    ``options`` updated to reflect the latest interaction in the browser.
    """
    if not isinstance(widget, GraphWidget):
        raise TypeError(f"Expected a GraphWidget, got {type(widget).__name__}")

    # `selected`/`options` are owned by the frontend once the user interacts with the
    # widget (selecting entities, switching layout, ...). Their latest values live in
    # the component's persisted state. Apply them to the widget *before* building the
    # data we push, so a rerun doesn't send the widget's initial values and reset the
    # UI. (Requires a `key` for Streamlit to persist the state across reruns.)
    persisted = _persisted_state(key)
    carried_over = {trait: persisted[trait] for trait in _RECEIVE_KEYS if persisted.get(trait) is not None}
    if carried_over:
        widget.set_state(carried_over)

    # get_state() applies each trait's to_json serializer (unlike a naive json.dumps
    # of the raw trait values), producing exactly the shape the frontend expects.
    state = widget.get_state()
    data = {trait: state[trait] for trait in _SEND_KEYS if trait in state}

    # The on_<name>_change callbacks (invoked by Streamlit with no arguments) only
    # need to register `selected`/`options` as state keys; the values are read from
    # `result` below, so the callbacks are no-ops.
    result = _component()(
        key=key,
        data=data,
        height=_component_height(state.get("height")),
        default={trait: None for trait in _RECEIVE_KEYS},
        on_selected_change=lambda *_a, **_k: None,
        on_options_change=lambda *_a, **_k: None,
    )

    # set_state() applies each trait's from_json serializer, so e.g. `selected`
    # becomes a GraphSelection and `options` a WidgetOptions again.
    incoming = {trait: result[trait] for trait in _RECEIVE_KEYS if result.get(trait) is not None}
    if incoming:
        widget.set_state(incoming)

    return widget
