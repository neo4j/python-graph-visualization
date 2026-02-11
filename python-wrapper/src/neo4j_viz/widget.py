from __future__ import annotations

import json
import os
from importlib.resources import files
from pathlib import Path
from typing import Union

import anywidget
import traitlets

from .node import Node
from .relationship import Relationship

_DEV = os.environ.get("NEO4J_VIZ_DEV", "").strip() not in ("", "0", "false")
_DEV_SERVER = os.environ.get("NEO4J_VIZ_DEV_SERVER", "http://localhost:5173")


def _serialize_entity(entity: Union[Node, Relationship]) -> dict[str, object]:
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


def _resource_path(filename: str) -> Path:
    base_folder = files("neo4j_viz")
    resource_folder = base_folder / "resources"
    nvl_entry_point = resource_folder / "nvl_entrypoint"
    path = nvl_entry_point / filename
    return Path(str(path))


def _get_esm() -> Union[str, Path]:
    """Return the ESM source — Vite dev server URL or bundled file path."""
    if _DEV:
        return f"{_DEV_SERVER}/src/index.tsx?anywidget"
    return _resource_path("widget.js")


def _get_css() -> Union[str, Path]:
    """Return the CSS source — empty string in dev (Vite serves it) or bundled file."""
    if _DEV:
        return ""
    return _resource_path("style.css")


class GraphWidget(anywidget.AnyWidget):  # type: ignore[misc]
    """Jupyter widget for interactive graph visualization.

    Uses anywidget to render a React-based graph component with
    two-way data sync between Python and JavaScript.

    Dev mode: set NEO4J_VIZ_DEV=1 and run `yarn dev` in js-applet/
    for hot module replacement during development.
    """

    _esm = _get_esm()
    _css = _get_css()

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
