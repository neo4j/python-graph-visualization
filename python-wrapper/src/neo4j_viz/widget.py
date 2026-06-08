from __future__ import annotations

import json
import pathlib
from functools import cached_property
from typing import Any, Union

import anywidget
import traitlets

from ._graph_entity_operations import GraphEntityOperations, delegate_doc
from .colors import ColorSpace, ColorsType
from .node import Node, NodeIdType
from .node_size import RealNumber
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


def entity_to_json(entity_list: list[Node | Relationship], widget: anywidget.AnyWidget) -> list[dict[str, Any]]:
    return [_serialize_entity(entity) for entity in entity_list]


class GraphWidget(anywidget.AnyWidget):
    """Jupyter widget for interactive graph visualization.

    Uses anywidget to render a React-based graph component with
    two-way data sync between Python and JavaScript.

    The widget exposes utility methods that mutate the graph in place and
    automatically sync the changes to the frontend.

    Dev mode: set ANYWIDGET_HMR=1 and run ``yarn dev`` in js-applet/
    for hot module replacement during development.
    """

    _esm = _STATIC / "widget.js"
    _css = _STATIC / "style.css"

    nodes: traitlets.List[Node] = traitlets.List([]).tag(sync=True, to_json=entity_to_json)
    relationships: traitlets.List[Relationship] = traitlets.List([]).tag(sync=True, to_json=entity_to_json)
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
            nodes=nodes,
            relationships=relationships,
            width=width,
            height=height,
            options=options.to_js_options() if options else {},
            theme=theme,
        )

    def __str__(self) -> str:
        return f"GraphWidget(nodes={len(self.nodes)}, relationships={len(self.relationships)}, options={self.options}, theme={self.theme}, width={self.width}, height={self.height})"

    @cached_property
    def _entity_ops(self) -> GraphEntityOperations:
        return GraphEntityOperations(self)

    def sync_nodes(self) -> None:
        """Manually trigger a sync of the `nodes` list to the frontend."""
        self._sync_entities(nodes=True)

    def sync_relationships(self) -> None:
        """Manually trigger a sync of the `relationships` list to the frontend."""
        self._sync_entities(relationships=True)

    def _sync_entities(self, *, nodes: bool = False, relationships: bool = False) -> None:
        """Propagate in-place entity mutations to the frontend.

        The utility methods delegated to :class:`GraphEntityOperations` mutate the `Node`
        and `Relationship` objects in place. This does not change the identity (or equality)
        of the `nodes`/`relationships` lists, so traitlets does not detect a change and would
        not sync. We therefore explicitly push the affected trait(s) to JavaScript, which
        re-serializes them via `entity_to_json`. When the widget is not connected to a
        frontend (e.g. outside a notebook), `send_state` is a no-op.
        """
        keys = []
        if nodes:
            keys.append("nodes")
        if relationships:
            keys.append("relationships")
        if keys:
            self.send_state(keys if len(keys) > 1 else keys[0])

    @delegate_doc(GraphEntityOperations.toggle_nodes_pinned)
    def toggle_nodes_pinned(self, pinned: dict[NodeIdType, bool]) -> None:
        self._entity_ops.toggle_nodes_pinned(pinned)

    @delegate_doc(GraphEntityOperations.set_node_captions)
    def set_node_captions(
        self,
        *,
        field: str | None = None,
        property: str | None = None,
        override: bool = True,
    ) -> None:
        self._entity_ops.set_node_captions(field=field, property=property, override=override)

    @delegate_doc(GraphEntityOperations.resize_nodes)
    def resize_nodes(
        self,
        sizes: dict[NodeIdType, RealNumber] | None = None,
        node_radius_min_max: tuple[RealNumber, RealNumber] | None = (3, 60),
        property: str | None = None,
    ) -> None:
        self._entity_ops.resize_nodes(sizes=sizes, node_radius_min_max=node_radius_min_max, property=property)

    @delegate_doc(GraphEntityOperations.resize_relationships)
    def resize_relationships(
        self,
        widths: dict[str | int, RealNumber] | None = None,
        property: str | None = None,
    ) -> None:
        self._entity_ops.resize_relationships(widths=widths, property=property)

    @delegate_doc(GraphEntityOperations.color_nodes)
    def color_nodes(
        self,
        *,
        field: str | None = None,
        property: str | None = None,
        colors: ColorsType | None = None,
        color_space: ColorSpace = ColorSpace.DISCRETE,
        override: bool = True,
    ) -> None:
        self._entity_ops.color_nodes(
            field=field, property=property, colors=colors, color_space=color_space, override=override
        )

    @delegate_doc(GraphEntityOperations.color_relationships)
    def color_relationships(
        self,
        *,
        field: str | None = None,
        property: str | None = None,
        colors: ColorsType | None = None,
        color_space: ColorSpace = ColorSpace.DISCRETE,
        override: bool = True,
    ) -> None:
        self._entity_ops.color_relationships(
            field=field, property=property, colors=colors, color_space=color_space, override=override
        )

    def add_data(
        self, nodes: Node | list[Node] | None = None, relationships: Relationship | list[Relationship] | None = None
    ) -> None:
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
            self.nodes = self.nodes + nodes
        if relationships:
            self.relationships = self.relationships + relationships

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
        elif nodes is None:
            node_ids_to_remove = set()
        else:
            node_ids_to_remove = {n.id if isinstance(n, Node) else n for n in nodes}

        if isinstance(relationships, Relationship):
            rel_ids_to_remove = {relationships.id}
        elif isinstance(relationships, RelationshipIdType):
            rel_ids_to_remove = {relationships}
        elif relationships is None:
            rel_ids_to_remove = set()
        else:
            rel_ids_to_remove = {r.id if isinstance(r, Relationship) else r for r in relationships}

        if node_ids_to_remove:
            self.nodes = [n for n in self.nodes if n.id not in node_ids_to_remove]

        def keep_rel(r: Relationship) -> bool:
            return (
                r.id not in rel_ids_to_remove
                and r.source not in node_ids_to_remove
                and r.target not in node_ids_to_remove
            )

        if rel_ids_to_remove:
            self.relationships = [r for r in self.relationships if keep_rel(r)]
