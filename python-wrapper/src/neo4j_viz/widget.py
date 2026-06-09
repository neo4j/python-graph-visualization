from __future__ import annotations

import json
import pathlib
from functools import cached_property
from typing import Any, Union, cast

import anywidget
import traitlets

from ._graph_entity_operations import GraphEntityOperations
from .colors import ColorSpace, ColorsType
from .node import Node, NodeIdType
from .node_size import RealNumber
from .options import (
    Layout,
    LayoutOptions,
    NvlOptionsDict,
    Renderer,
    RenderOptions,
    RenderOptionsDict,
    construct_layout_options,
)
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


# Dev mode: set ANYWIDGET_HMR=1 and run ``yarn dev`` in js-applet/
# for hot module replacement during development.


class GraphWidget(anywidget.AnyWidget):
    """Jupyter widget for interactive graph visualization.

    Uses anywidget to render a React-based graph component with
    two-way data sync between Python and JavaScript.

    The widget exposes utility methods that mutate the graph in place and
    automatically sync the changes to the frontend.
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

    def toggle_nodes_pinned(self, pinned: dict[NodeIdType, bool]) -> None:
        """
        Toggle whether nodes should be pinned or not.

        Parameters
        ----------
        pinned:
            A dictionary mapping from node ID to whether the node should be pinned or not.
        """
        self._entity_ops.toggle_nodes_pinned(pinned)

    def set_node_captions(
        self,
        *,
        field: str | None = None,
        property: str | None = None,
        override: bool = True,
    ) -> None:
        """
        Set the caption for nodes in the graph based on either a node field or a node property.

        Parameters
        ----------
        field:
            The field of the nodes to use as the caption. Must be None if `property` is provided.
        property:
            The property of the nodes to use as the caption. Must be None if `field` is provided.
        override:
            Whether to override existing captions of the nodes, if they have any.

        Examples
        --------
        Given a GraphWidget `widget`:

        >>> nodes = [
        ...    Node(id="0", properties={"name": "Alice", "age": 30}),
        ...    Node(id="1", properties={"name": "Bob", "age": 25}),
        ... ]
        >>> widget = GraphWidget(nodes=nodes)

        Set node captions from a property:

        >>> widget.set_node_captions(property="name")

        Set node captions from a field, only if not already set:

        >>> widget.set_node_captions(field="id", override=False)
        """
        self._entity_ops.set_node_captions(field=field, property=property, override=override)

    def resize_nodes(
        self,
        sizes: dict[NodeIdType, RealNumber] | None = None,
        node_radius_min_max: tuple[RealNumber, RealNumber] | None = (3, 60),
        property: str | None = None,
    ) -> None:
        """
        Resize the nodes in the graph.

        Parameters
        ----------
        sizes:
            A dictionary mapping from node ID to the new size of the node.
            If a node ID is not in the dictionary, the size of the node is not changed.
            Must be None if `property` is provided.
        node_radius_min_max:
            Minimum and maximum node size radius as a tuple. To avoid tiny or huge nodes in the visualization, the
            node sizes are scaled to fit in the given range. If None, the sizes are used as is.
        property:
            The property of the nodes to use for sizing. Must be None if `sizes` is provided.
        """
        self._entity_ops.resize_nodes(sizes=sizes, node_radius_min_max=node_radius_min_max, property=property)

    def resize_relationships(
        self,
        widths: dict[str | int, RealNumber] | None = None,
        property: str | None = None,
    ) -> None:
        """
        Resize the width of relationships in the graph.

        Parameters
        ----------
        widths:
            A dictionary mapping from relationship ID to the new width of the relationship.
            If a relationship ID is not in the dictionary, the width of the relationship is not changed.
            Must be None if `property` is provided.
        property:
            The property of the relationships to use for sizing. Must be None if `widths` is provided.
        """
        self._entity_ops.resize_relationships(widths=widths, property=property)

    def color_nodes(
        self,
        *,
        field: str | None = None,
        property: str | None = None,
        colors: ColorsType | None = None,
        color_space: ColorSpace = ColorSpace.DISCRETE,
        override: bool = True,
    ) -> None:
        """
        Color the nodes in the graph based on either a node field, or a node property.

        It's possible to color the nodes based on a discrete or continuous color space. In the discrete case, a new
        color from the `colors` provided is assigned to each unique value of the node field/property.
        In the continuous case, the `colors` should be a list of colors representing a range that are used to
        create a gradient of colors based on the values of the node field/property.

        Parameters
        ----------
        field:
            The field of the nodes to base the coloring on. The type of this field must be hashable, or be a
            list, set or dict containing only hashable types. Must be None if `property` is provided.
        property:
            The property of the nodes to base the coloring on. The type of this property must be hashable, or be a
            list, set or dict containing only hashable types. Must be None if `field` is provided.
        colors:
            The colors to use for the nodes.
            If `color_space` is `ColorSpace.DISCRETE`, the colors can be a dictionary mapping from field/property value
            to color, or an iterable of colors in which case the colors are used in order.
            If `color_space` is `ColorSpace.CONTINUOUS`, the colors must be a list of colors representing a range.
            Allowed color values are for example “#FF0000”, “red” or (255, 0, 0) (full list: https://docs.pydantic.dev/2.0/usage/types/extra_types/color_types/).
            The default colors are the Neo4j graph colors.
        color_space:
            The type of space of the provided `colors`. Either `ColorSpace.DISCRETE` or `ColorSpace.CONTINUOUS`. It determines whether
            colors are assigned based on unique field/property values or a gradient of the values of the field/property.
        override:
            Whether to override existing colors of the nodes, if they have any.

        Examples
        --------

        Given a GraphWidget `widget`:

        >>> nodes = [
        ...    Node(id="0", properties={"label": "Person", "score": 10}),
        ...    Node(id="1", properties={"label": "Person", "score": 20}),
        ... ]
        >>> widget = GraphWidget(nodes=nodes)

        Color nodes based on a discrete field such as "label":

        >>> widget.color_nodes(field="label", color_space=ColorSpace.DISCRETE)

        Color nodes based on a continuous field such as "score":

        >>> widget.color_nodes(field="score", color_space=ColorSpace.CONTINUOUS)

        Color nodes based on a custom colors such as from palettable:

        >>> from palettable.wesanderson import Moonrise1_5  # type: ignore[import-untyped]
        >>> widget.color_nodes(field="label", colors=Moonrise1_5.colors)
        """
        self._entity_ops.color_nodes(
            field=field, property=property, colors=colors, color_space=color_space, override=override
        )

    def color_relationships(
        self,
        *,
        field: str | None = None,
        property: str | None = None,
        colors: ColorsType | None = None,
        color_space: ColorSpace = ColorSpace.DISCRETE,
        override: bool = True,
    ) -> None:
        """
        Color the relationships in the graph based on either a relationship field, or a relationship property.

        It's possible to color the relationships based on a discrete or continuous color space. In the discrete case,
        a new color from the `colors` provided is assigned to each unique value of the relationship field/property.
        In the continuous case, the `colors` should be a list of colors representing a range that are used to
        create a gradient of colors based on the values of the relationship field/property.

        Parameters
        ----------
        field:
            The field of the relationships to base the coloring on. The type of this field must be hashable, or be a
            list, set or dict containing only hashable types. Must be None if `property` is provided.
        property:
            The property of the relationships to base the coloring on. The type of this property must be hashable, or be a
            list, set or dict containing only hashable types. Must be None if `field` is provided.
        colors:
            The colors to use for the relationships.
            If `color_space` is `ColorSpace.DISCRETE`, the colors can be a dictionary mapping from field/property value
            to color, or an iterable of colors in which case the colors are used in order.
            If `color_space` is `ColorSpace.CONTINUOUS`, the colors must be a list of colors representing a range.
            Allowed color values are for example “#FF0000”, “red” or (255, 0, 0) (full list: https://docs.pydantic.dev/2.0/usage/types/extra_types/color_types/).
            The default colors are the Neo4j graph colors.
        color_space:
            The type of space of the provided `colors`. Either `ColorSpace.DISCRETE` or `ColorSpace.CONTINUOUS`. It determines whether
            colors are assigned based on unique field/property values or a gradient of the values of the field/property.
        override:
            Whether to override existing colors of the relationships, if they have any.

        Examples
        --------

        Given a GraphWidget `widget`:

        >>> nodes = [Node(id="0"), Node(id="1")]
        >>> relationships = [
        ...    Relationship(source="0", target="1", caption="ACTED_IN", properties={"score": 10}),
        ...    Relationship(source="1", target="0", caption="DIRECTED", properties={"score": 20}),
        ... ]
        >>> widget = GraphWidget(nodes=nodes, relationships=relationships)

        Color relationships based on a discrete field such as "caption":

        >>> widget.color_relationships(field="caption", color_space=ColorSpace.DISCRETE)

        Color relationships based on a continuous field such as "score":

        >>> widget.color_relationships(property="score", color_space=ColorSpace.CONTINUOUS)
        """
        self._entity_ops.color_relationships(
            field=field, property=property, colors=colors, color_space=color_space, override=override
        )

    def _render_options(self) -> RenderOptionsDict:
        """Return a typed, mutable copy of the current JS-shaped render options."""
        return cast(RenderOptionsDict, dict(self.options))

    def set_layout(self, layout: Layout | str, layout_options: dict[str, Any] | LayoutOptions | None = None) -> None:
        """
        Change the layout algorithm used to position the graph, in place.

        Parameters
        -----------
        layout:
            The layout algorithm to use (e.g. `Layout.FORCE_DIRECTED`, `Layout.HIERARCHICAL`).
        layout_options:
            Optional layout-specific options. Either a `HierarchicalLayoutOptions`/`ForceDirectedLayoutOptions`
            instance or a plain dict, which is validated against the chosen layout. Layout options are only
            supported for the force-directed and hierarchical layouts.
        """
        if isinstance(layout, str):
            layout = Layout(layout)

        if isinstance(layout_options, dict):
            layout_options = construct_layout_options(layout, layout_options)

        js = RenderOptions(layout=layout, layout_options=layout_options).to_js_options()

        new = self._render_options()
        new["layout"] = js["layout"]
        if "layoutOptions" in js:
            new["layoutOptions"] = js["layoutOptions"]
        else:
            new.pop("layoutOptions", None)
        self.options = dict(new)

    def set_zoom(self, zoom: float) -> None:
        """
        Change the zoom level of the graph, in place.

        Parameters
        -----------
        zoom:
            The zoom level to apply.
        """
        new = self._render_options()
        new["zoom"] = zoom
        self.options = dict(new)

    def set_pan(self, x: float, y: float) -> None:
        """
        Change the pan position of the graph, in place.

        Parameters
        -----------
        x:
            The pan position along the x-axis.
        y:
            The pan position along the y-axis.
        """
        new = self._render_options()
        new["pan"] = {"x": x, "y": y}
        self.options = dict(new)

    def set_renderer(self, renderer: Renderer) -> None:
        """
        Change the renderer used to draw the graph, in place.

        Parameters
        -----------
        renderer:
            The renderer to use, either `Renderer.WEB_GL` or `Renderer.CANVAS`.
        """
        Renderer.check(renderer, len(self.nodes))

        new = self._render_options()
        nvl_options = cast(NvlOptionsDict, dict(new.get("nvlOptions", {})))
        nvl_options["disableWebGL"] = renderer != Renderer.WEB_GL
        new["nvlOptions"] = nvl_options
        self.options = dict(new)

    def set_show_layout_button(self, show: bool = True) -> None:
        """
        Toggle the layout selector button in the widget UI, in place.

        Parameters
        -----------
        show:
            Whether the layout button should be shown.
        """
        new = self._render_options()
        new["showLayoutButton"] = show
        self.options = dict(new)

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
