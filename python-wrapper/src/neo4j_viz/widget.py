from __future__ import annotations

import json
import pathlib
from typing import Any, Union

import anywidget
import traitlets

from .node import Node, NodeIdType
from .options import RenderOptions
from .relationship import Relationship, RelationshipIdType


def _serialize_entity(entity: Union[Node, Relationship]) -> dict[str, Any]:
    """Convert a Node or Relationship to a JSON-serializable dict.

    Returns a dict (not a JSON string) because traitlets.List expects Python objects,
    not pre-serialized strings. Traitlets handles JSON serialization for transport to JS.
    See: https://traitlets.readthedocs.io/en/stable/config.html#serializing-values
    """
    try:
        entity_dict = entity.to_dict()
        # Verify it's JSON-serializable
        json.dumps(entity_dict)
        return entity_dict
    except TypeError:
        props_as_strings: dict[str, str] = {}
        for k, v in entity_dict["properties"].items():
            try:
                json.dumps(v)
            except TypeError:
                props_as_strings[k] = str(v)
        entity_dict["properties"].update(props_as_strings)
        return entity_dict


_STATIC = pathlib.Path(__file__).parent / "resources" / "nvl_entrypoint"


class GraphWidget(anywidget.AnyWidget):
    """Jupyter widget for interactive graph visualization.

    Uses anywidget to render a React-based graph component with
    two-way data sync between Python and JavaScript.

    Dev mode: set ANYWIDGET_HMR=1 and run ``yarn dev`` in js-applet/
    for hot module replacement during development.
    """

    _esm = _STATIC / "widget.js"
    _css = _STATIC / "style.css"

    nodes: traitlets.List[dict[str, Any]] = traitlets.List([]).tag(sync=True)
    relationships: traitlets.List[dict[str, Any]] = traitlets.List([]).tag(sync=True)
    width: traitlets.Unicode[str, str | bytes] = traitlets.Unicode("100%").tag(sync=True)
    height: traitlets.Unicode[str, str | bytes] = traitlets.Unicode("600px").tag(sync=True)
    options: traitlets.Dict[str, Any] = traitlets.Dict({}).tag(sync=True)
    theme: traitlets.Unicode[str, str | bytes] = traitlets.Unicode(
        default_value="auto", help="Theme of the graph widget. Can be 'auto', 'light', or 'dark'."
    ).tag(sync=True)

    @classmethod
    def from_graph_data(
        cls,
        nodes: list[Node],
        relationships: list[Relationship],
        width: str = "100%",
        height: str = "600px",
        options: RenderOptions | None = None,
        theme: str = "auto",
    ) -> GraphWidget:
        """Create a GraphWidget from Node and Relationship lists."""
        return cls(
            nodes=[_serialize_entity(n) for n in nodes],
            relationships=[_serialize_entity(r) for r in relationships],
            width=width,
            height=height,
            options=options.to_js_options() if options else {},
            theme=theme,
        )

    def add_data(self, nodes: Node | list[Node] | None = None, relationships: Relationship | list[Relationship] | None = None) -> None:
        """
        Add nodes or relationships to the graph widget.

        Parameters
        -----------
        nodes:
            Nodes to add to the graph widget.
        relationships:
            Relationships to add to the graph widget.
        """
        if isinstance(nodes, Node):
            nodes = [nodes]
        if isinstance(relationships, Relationship):
            relationships = [relationships]

        if nodes:
            self.nodes = self.nodes + [_serialize_entity(n) for n in nodes]
        if relationships:
            self.relationships = self.relationships + [_serialize_entity(r) for r in relationships]

    def remove_data(
        self,
        nodes: Node | list[Node | NodeIdType] | NodeIdType | None = None,
        relationships: Relationship | list[Relationship | RelationshipIdType] | RelationshipIdType | None = None,
    ) -> None:
        """
        Remove nodes or relationships from the graph widget.

        Parameters
        -----------
        nodes:
            Nodes to remove from the graph widget.
        relationships:
            Relationships to remove from the graph widget.
        """
        if isinstance(nodes, Node):
            node_ids_to_remove = {nodes.id}
        elif isinstance(nodes, NodeIdType):
            node_ids_to_remove = {nodes}
        else:
            node_ids_to_remove = {n.id if isinstance(n, Node) else n for n in nodes}

        if isinstance(relationships, Relationship):
            rel_ids_to_remove = {relationships.id}
        elif isinstance(relationships, RelationshipIdType):
            rel_ids_to_remove = {relationships}
        else:
            rel_ids_to_remove = {r.id if isinstance(r, Relationship) else r for r in relationships}

        self.nodes = [n for n in self.nodes if n["id"] not in node_ids_to_remove]

        def keep_rel(r: dict[str, Any]) -> bool:
            return (
                r["id"] not in rel_ids_to_remove
                and r["from"] not in node_ids_to_remove
                and r["to"] not in node_ids_to_remove
            )

        self.relationships = [r for r in self.relationships if keep_rel(r)]
