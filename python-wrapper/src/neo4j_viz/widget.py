from __future__ import annotations

import json
import pathlib
from typing import Union

import anywidget
import traitlets

from .node import Node
from .relationship import Relationship


def _serialize_entity(entity: Union[Node, Relationship]) -> dict[str, object]:
    """Convert a Node or Relationship to a JSON-serializable dict.

    Returns a dict (not a JSON string) because traitlets.List expects Python objects,
    not pre-serialized strings. Traitlets handles JSON serialization for transport to JS.
    See: https://traitlets.readthedocs.io/en/stable/config.html#serializing-values
    """
    try:
        entity_dict = entity.to_dict()
        # Verify it's JSON-serializable
        json.dumps(entity_dict)
        return entity_dict  # type: ignore[return-value]
    except TypeError:
        props_as_strings: dict[str, str] = {}
        for k, v in entity_dict["properties"].items():
            try:
                json.dumps(v)
            except TypeError:
                props_as_strings[k] = str(v)
        entity_dict["properties"].update(props_as_strings)
        return entity_dict  # type: ignore[return-value]


_STATIC = pathlib.Path(__file__).parent / "resources" / "nvl_entrypoint"


class GraphWidget(anywidget.AnyWidget):  # type: ignore[misc]
    """Jupyter widget for interactive graph visualization.

    Uses anywidget to render a React-based graph component with
    two-way data sync between Python and JavaScript.

    Dev mode: set ANYWIDGET_HMR=1 and run ``yarn dev`` in js-applet/
    for hot module replacement during development.
    """

    _esm = _STATIC / "widget.js"
    _css = _STATIC / "style.css"

    nodes = traitlets.List([]).tag(sync=True)  # type: ignore[assignment]
    relationships = traitlets.List([]).tag(sync=True)  # type: ignore[assignment]
    width = traitlets.Unicode("100%").tag(sync=True)  # type: ignore[assignment]
    height = traitlets.Unicode("600px").tag(sync=True)  # type: ignore[assignment]
    options = traitlets.Dict({}).tag(sync=True)

    @classmethod
    def from_graph_data(
        cls,
        nodes: list[Node],
        relationships: list[Relationship],
        width: str = "100%",
        height: str = "600px",
        options: dict[str, object] | None = None,
    ) -> GraphWidget:
        """Create a GraphWidget from Node and Relationship lists."""
        return cls(
            nodes=[_serialize_entity(n) for n in nodes],
            relationships=[_serialize_entity(r) for r in relationships],
            width=width,
            height=height,
            options=options or {},
        )
