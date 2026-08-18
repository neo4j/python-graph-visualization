"""Streamlit integration for :class:`~neo4j_viz.widget.GraphWidget`.

Streamlit doesn't speak the Jupyter/anywidget comm protocol, so a ``GraphWidget``
can't be embedded the way it is in a notebook.

This module bridges the same React frontend (reused from the notebook widget) as a
`Streamlit Components v2` component, using the widget's
own ``get_state``/``set_state``. Selection and option changes made in the browser flow back to the
Python ``GraphWidget`` on the next rerun.

Example
-------
>>> import streamlit as st
>>> from neo4j_viz import Node, Relationship, VisualizationGraph
>>> from neo4j_viz.streamlit import display_widget
>>>
>>> vg = VisualizationGraph(nodes=[Node(id="0"), Node(id="1")], relationships=[])
>>> widget = vg.render_widget()
>>> display_widget(widget, key="graph")
>>> st.write("Selected nodes:", widget.selected.nodeIds)
"""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from typing import Any, Literal

try:
    import streamlit as st
except ImportError as exc:
    raise ImportError(
        "neo4j_viz.streamlit requires the optional 'streamlit' dependency "
        "(streamlit>=1.58, for the Components v2 API). "
        "Install it with: pip install 'neo4j-viz[streamlit]'"
    ) from exc

from streamlit.components.v2 import component
from streamlit.components.v2.types import ComponentRenderer

from .widget import GraphWidget

# Traits pushed to the frontend on every render. Mirrors the sync traits that the
# JS component reads (see js-applet/src/graph-widget.tsx).
_SEND_KEYS = ("nodes", "relationships", "options", "width", "height", "theme", "selected", "legend")

# Traits the frontend may write back to Python. Must stay in sync with
# WRITABLE_KEYS in js-applet/src/streamlit-entrypoint.ts.
_RECEIVE_KEYS = ("selected", "options", "last_event")


@lru_cache(maxsize=1)
def _component_renderer() -> ComponentRenderer:
    """Declare (once per process) the Streamlit v2 component.

    The frontend is the self-contained ES module produced by the ``build:streamlit``
    step and shipped as package data. It is passed inline (rather than served from an
    ``asset_dir``, which requires a package manifest that is unreliable for installed
    wheels); Streamlit's ForwardMsg cache dedupes the payload across reruns.
    """
    resources = files("neo4j_viz") / "resources" / "streamlit_v2"
    # Prepend a marker comment to not confuse with file path
    js = "// neo4j-viz streamlit component\n" + (resources / "graph.js").read_text(encoding="utf-8")
    css = "/* neo4j-viz streamlit component */\n" + (resources / "style.css").read_text(encoding="utf-8")
    return component("neo4j_viz_graph", js=js, css=css)


def _sync_persisted_to_widget(widget: GraphWidget, key: str) -> None:
    try:
        persisted = st.session_state[key]
    except Exception:
        return
    if isinstance(persisted, dict):
        _apply_frontend_traits(widget, persisted)


def _sync_result_to_widget(widget: GraphWidget, result: Any) -> None:
    _apply_frontend_traits(widget, result)


def _apply_frontend_traits(widget: GraphWidget, source: Any) -> None:
    """Write the frontend-owned traits (``_RECEIVE_KEYS``) from ``source`` into the
    widget, skipping absent/None entries."""
    incoming = {trait: source[trait] for trait in _RECEIVE_KEYS if source.get(trait) is not None}
    if incoming:
        widget.set_state(incoming)


def _component_height(height: Any) -> int | Literal["content"]:
    """Map the widget's height to a streamlit ``height`` argument."""
    if isinstance(height, str) and height.endswith("px"):
        try:
            return int(float(height[:-2]))
        except ValueError:
            pass
    return "content"


def display_widget(any_widget: GraphWidget, *, key: str = "neo4j-viz-widget") -> None:
    """Display a :class:`~neo4j_viz.widget.GraphWidget` in a Streamlit app with two-way sync.

    Displays the same interactive visualization as the widget does in a notebook
    (pan/zoom, selection, layout switching, legend, side panel). Changes made in the
    browser to the selection and render options are synced back into ``any_widget``
    *in place* on the next Streamlit rerun, so they can be read from Python
    (e.g. ``any_widget.selected``) and reacted to. Nothing is returned -- keep a
    reference to the widget you pass in and read the synced state off it.

    Parameters
    ----------
    any_widget:
        A :class:`~neo4j_viz.widget.GraphWidget`, as returned by
        :meth:`VisualizationGraph.render_widget`.
    key:
        A stable, unique Streamlit widget key. It lets Streamlit persist the widget's
        ``selected``/``options`` state across reruns, so interactions like changing the
        layout or selecting nodes are not reset on the next rerun. Defaults to
        ``"neo4j-viz-widget"``; when rendering more
        than one graph in the same app, give each a distinct ``key``.
    """
    if not isinstance(any_widget, GraphWidget):
        raise TypeError(f"Expected a GraphWidget, got {type(any_widget).__name__}")

    # `selected`/`options` are owned by the frontend once the user interacts with the
    # widget (selecting entities, switching layout, ...); apply their persisted values
    # before building the data we push, so a rerun doesn't reset the UI.
    _sync_persisted_to_widget(any_widget, key)

    state = any_widget.get_state()
    result = _component_renderer()(
        key=key,
        data={trait: state[trait] for trait in _SEND_KEYS if trait in state},
        height=_component_height(state.get("height")),
        default={trait: None for trait in _RECEIVE_KEYS},
        on_selected_change=lambda *_a, **_k: None,  # register `selected` as a state key
        on_options_change=lambda *_a, **_k: None,  # register `options` as a state key
        on_last_event_change=lambda *_a, **_k: None,  # register `last_event` as a state key
    )

    # `result` holds the browser's current values only *after* the render; apply them
    # so the widget reflects this rerun's interaction.
    _sync_result_to_widget(any_widget, result)
