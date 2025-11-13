from __future__ import annotations

import warnings
from collections.abc import Iterable
from typing import Any, Callable, Hashable, Optional, Union

from IPython.display import HTML
from pydantic.alias_generators import to_snake
from pydantic_extra_types.color import Color, ColorType

from .colors import NEO4J_COLORS_CONTINUOUS, NEO4J_COLORS_DISCRETE, ColorSpace, ColorsType
from .node import Node, NodeIdType
from .node_size import RealNumber, verify_radii
from .nvl import NVL
from .options import (
    Layout,
    LayoutOptions,
    Renderer,
    RenderOptions,
    construct_layout_options,
)
from .relationship import Relationship


# TODO helper for map properties to fields. helper for set caption (simplicity)
class VisualizationGraph:
    """
    A graph to visualize.

    The `VisualizationGraph` class represents a collection of nodes and relationships that can be
    rendered as an interactive graph visualization. You can customize the appearance of nodes and
    relationships by setting their properties, colors, sizes, and other visual attributes.
    """

    #: "The nodes in the graph"
    nodes: list[Node]
    #: "The relationships in the graph"
    relationships: list[Relationship]

    def __init__(self, nodes: list[Node], relationships: list[Relationship]) -> None:
        """
        Parameters
        ----------
        nodes : list[Node]
            The nodes in the graph.
        relationships : list[Relationship]
            The relationships in the graph.

        Examples
        --------
        Basic usage with nodes and relationships:

        >>> from neo4j_viz import Node, Relationship, VisualizationGraph
        >>> nodes = [
        ...     Node(id="1", properties={"name": "Alice", "age": 30}),
        ...     Node(id="2", properties={"name": "Bob", "age": 25}),
        ... ]
        >>> relationships = [
        ...     Relationship(id="r1", source="1", target="2", properties={"type": "KNOWS"})
        ... ]
        >>> VG = VisualizationGraph(nodes=nodes, relationships=relationships)

        Setting a node field such as captions from properties:

        >>> # Set caption from a specific property
        >>> for node in VG.nodes:
        ...     node.caption = node.properties.get("name")

        Setting a relationship field such as type from properties:

        >>> # Set relationship caption from property
        >>> for rel in VG.relationships:
        ...     rel.caption = rel.properties.get("type")

        Using built-in helper methods:

        >>> # Use the color_nodes method for automatic coloring
        >>> VG.color_nodes(property="age", color_space=ColorSpace.CONTINUOUS)
        >>>
        >>> # Use resize_nodes for automatic sizing
        >>> VG.resize_nodes(property="degree", node_radius_min_max=(10, 50))

        """
        self.nodes = nodes
        self.relationships = relationships

    def render(
        self,
        layout: Optional[Layout] = None,
        layout_options: Union[dict[str, Any], LayoutOptions, None] = None,
        renderer: Renderer = Renderer.CANVAS,
        width: str = "100%",
        height: str = "600px",
        pan_position: Optional[tuple[float, float]] = None,
        initial_zoom: Optional[float] = None,
        min_zoom: float = 0.075,
        max_zoom: float = 10,
        allow_dynamic_min_zoom: bool = True,
        max_allowed_nodes: int = 10_000,
        show_hover_tooltip: bool = True,
    ) -> HTML:
        """
        Render the graph.

        Parameters
        ----------
        layout:
            The `Layout` to use.
        layout_options:
            The `LayoutOptions` to use.
        renderer:
            The `Renderer` to use.
        width:
            The width of the rendered graph.
        height:
            The height of the rendered graph.
        pan_position:
            The initial pan position.
        initial_zoom:
            The initial zoom level.
        min_zoom:
            The minimum zoom level.
        max_zoom:
            The maximum zoom level.
        allow_dynamic_min_zoom:
            Whether to allow dynamic minimum zoom level.
        max_allowed_nodes:
            The maximum allowed number of nodes to render.
        show_hover_tooltip:
            Whether to show an info tooltip when hovering over nodes and relationships.


        Example
        -------
        Basic rendering of a VisualizationGraph:
        >>> from neo4j_viz import Node, Relationship, VisualizationGraph
        """

        num_nodes = len(self.nodes)
        if num_nodes > max_allowed_nodes:
            raise ValueError(
                f"Too many nodes ({num_nodes}) to render. Maximum allowed nodes is set "
                f"to {max_allowed_nodes} for performance reasons. It can be increased by "
                "overriding `max_allowed_nodes`, but rendering could then take a long time"
            )

        Renderer.check(renderer, num_nodes)

        if not layout:
            layout = Layout.FORCE_DIRECTED
        if not layout_options:
            layout_options = {}

        if isinstance(layout_options, dict):
            layout_options_typed = construct_layout_options(layout, layout_options)
        else:
            layout_options_typed = layout_options

        render_options = RenderOptions(
            layout=layout,
            layout_options=layout_options_typed,
            renderer=renderer,
            pan_X=pan_position[0] if pan_position is not None else None,
            pan_Y=pan_position[1] if pan_position is not None else None,
            initial_zoom=initial_zoom,
            min_zoom=min_zoom,
            max_zoom=max_zoom,
            allow_dynamic_min_zoom=allow_dynamic_min_zoom,
        )

        return NVL().render(
            self.nodes,
            self.relationships,
            render_options,
            width,
            height,
            show_hover_tooltip,
        )

    def toggle_nodes_pinned(self, pinned: dict[NodeIdType, bool]) -> None:
        """
        Toggle whether nodes should be pinned or not.

        Parameters
        ----------
        pinned:
            A dictionary mapping from node ID to whether the node should be pinned or not.
        """
        for node in self.nodes:
            node_pinned = pinned.get(node.id)

            if node_pinned is None:
                continue

            node.pinned = node_pinned

    def set_node_captions(
        self,
        *,
        field: Optional[str] = None,
        property: Optional[str] = None,
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
        Given a VisualizationGraph `VG`:

        >>> nodes = [
        ...    Node(id="0", properties={"name": "Alice", "age": 30}),
        ...    Node(id="1", properties={"name": "Bob", "age": 25}),
        ... ]
        >>> VG = VisualizationGraph(nodes=nodes)

        Set node captions from a property:

        >>> VG.set_node_captions(property="name")

        Set node captions from a field, only if not already set:

        >>> VG.set_node_captions(field="id", override=False)

        Set captions from multiple properties with fallback:

        >>> for node in VG.nodes:
        ...     caption = node.properties.get("name") or node.properties.get("title") or node.id
        ...     if override or node.caption is None:
        ...         node.caption = str(caption)
        """
        if not ((field is None) ^ (property is None)):
            raise ValueError(
                f"Exactly one of the arguments `field` (received '{field}') and `property` (received '{property}') must be provided"
            )

        if property:
            # Use property
            for node in self.nodes:
                if not override and node.caption is not None:
                    continue

                value = node.properties.get(property, "")
                node.caption = str(value)
        else:
            # Use field
            assert field is not None
            attribute = to_snake(field)

            for node in self.nodes:
                if not override and node.caption is not None:
                    continue

                value = getattr(node, attribute, "")
                node.caption = str(value)

    def resize_nodes(
        self,
        sizes: Optional[dict[NodeIdType, RealNumber]] = None,
        node_radius_min_max: Optional[tuple[RealNumber, RealNumber]] = (3, 60),
        property: Optional[str] = None,
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
        if sizes is not None and property is not None:
            raise ValueError("At most one of the arguments `sizes` and `property` can be provided")

        if sizes is None and property is None and node_radius_min_max is None:
            raise ValueError("At least one of `sizes`, `property` or `node_radius_min_max` must be given")

        # Gather node sizes
        all_sizes = {}
        if sizes is not None:
            for node in self.nodes:
                size = sizes.get(node.id, node.size)
                if size is not None:
                    all_sizes[node.id] = size
        elif property is not None:
            for node in self.nodes:
                size = node.properties.get(property, node.size)
                if size is not None:
                    all_sizes[node.id] = size
        else:
            for node in self.nodes:
                if node.size is not None:
                    all_sizes[node.id] = node.size

        # Validate node sizes
        for id, size in all_sizes.items():
            if size is None:
                continue

            if not isinstance(size, (int, float)):
                raise ValueError(f"Size for node '{id}' must be a real number, but was {size}")

            if size < 0:
                raise ValueError(f"Size for node '{id}' must be non-negative, but was {size}")

        if node_radius_min_max is not None:
            verify_radii(node_radius_min_max)

            final_sizes = self._normalize_values(all_sizes, node_radius_min_max)
        else:
            final_sizes = all_sizes

        # Apply the final sizes to the nodes
        for node in self.nodes:
            size = final_sizes.get(node.id)

            if size is None:
                continue

            node.size = size

    @staticmethod
    def _normalize_values(
        node_map: dict[NodeIdType, RealNumber], min_max: tuple[float, float] = (0, 1)
    ) -> dict[NodeIdType, RealNumber]:
        unscaled_min_size = min(node_map.values())
        unscaled_max_size = max(node_map.values())
        unscaled_size_range = float(unscaled_max_size - unscaled_min_size)

        new_min_size, new_max_size = min_max
        new_size_range = new_max_size - new_min_size

        if abs(unscaled_size_range) < 1e-6:
            default_node_size = new_min_size + new_size_range / 2.0
            new_map = {id: default_node_size for id in node_map}
        else:
            new_map = {
                id: new_min_size + new_size_range * ((nz - unscaled_min_size) / unscaled_size_range)
                for id, nz in node_map.items()
            }

        return new_map

    def color_nodes(
        self,
        *,
        field: Optional[str] = None,
        property: Optional[str] = None,
        colors: Optional[ColorsType] = None,
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

        Given a VisualizationGraph `VG`:

        >>> nodes = [
        ...    Node(id="0", properties={"label": "Person", "score": 10}),
        ...    Node(id="1", properties={"label": "Person", "score": 20}),
        ... ]
        >>> VG = VisualizationGraph(nodes=nodes)

        Color nodes based on a discrete field such as "label":
        >>> VG.color_nodes(field="label", color_space=ColorSpace.DISCRETE)

        Color nodes based on a continuous field such as "score":

        >>> VG.color_nodes(field="score", color_space=ColorSpace.CONTINUOUS)

        Color nodes based on a custom colors such as from palettable:

        >>> from palettable.wesanderson import Moonrise1_5  # type: ignore[import-untyped]
        >>> VG.color_nodes(field="label", colors=Moonrise1_5.colors)
        """
        if not ((field is None) ^ (property is None)):
            raise ValueError(
                f"Exactly one of the arguments `field` (received '{field}') and `property` (received '{property}') must be provided"
            )

        if field is None:
            assert property is not None
            attribute = property

            def node_to_attr(node: Node) -> Any:
                return node.properties.get(attribute)
        else:
            assert field is not None
            attribute = to_snake(field)

            def node_to_attr(node: Node) -> Any:
                return getattr(node, attribute)

        if color_space == ColorSpace.DISCRETE:
            if colors is None:
                colors = NEO4J_COLORS_DISCRETE
        else:
            node_map = {node.id: node_to_attr(node) for node in self.nodes if node_to_attr(node) is not None}
            normalized_map = self._normalize_values(node_map)

            if colors is None:
                colors = NEO4J_COLORS_CONTINUOUS

            if not isinstance(colors, list):
                raise ValueError("For continuous properties, `colors` must be a list of colors representing a range")

            num_colors = len(colors)
            colors = {
                node_to_attr(node): colors[round(normalized_map[node.id] * (num_colors - 1))]
                for node in self.nodes
                if node_to_attr(node) is not None
            }

        if isinstance(colors, dict):
            self._color_nodes_dict(colors, override, node_to_attr)
        else:
            self._color_nodes_iter(attribute, colors, override, node_to_attr)

    def _color_nodes_dict(
        self, colors: dict[str, ColorType], override: bool, node_to_attr: Callable[[Node], Any]
    ) -> None:
        for node in self.nodes:
            color = colors.get(node_to_attr(node))

            if color is None:
                continue

            if node.color is not None and not override:
                continue

            if not isinstance(color, Color):
                node.color = Color(color)
            else:
                node.color = color

    def _color_nodes_iter(
        self, attribute: str, colors: Iterable[ColorType], override: bool, node_to_attr: Callable[[Node], Any]
    ) -> None:
        exhausted_colors = False
        prop_to_color = {}
        colors_iter = iter(colors)
        for node in self.nodes:
            raw_prop = node_to_attr(node)
            try:
                prop = self._make_hashable(raw_prop)
            except ValueError:
                raise ValueError(f"Unable to color nodes by unhashable property type '{type(raw_prop)}'")

            if prop not in prop_to_color:
                next_color = next(colors_iter, None)
                if next_color is None:
                    exhausted_colors = True
                    colors_iter = iter(colors)
                    next_color = next(colors_iter)
                prop_to_color[prop] = next_color

            color = prop_to_color[prop]

            if node.color is not None and not override:
                continue

            if not isinstance(color, Color):
                node.color = Color(color)
            else:
                node.color = color

        if exhausted_colors:
            warnings.warn(
                f"Ran out of colors for property '{attribute}'. {len(prop_to_color)} colors were needed, but only "
                f"{len(set(prop_to_color.values()))} were given, so reused colors"
            )

    @staticmethod
    def _make_hashable(raw_prop: Any) -> Hashable:
        prop = raw_prop
        if isinstance(raw_prop, list):
            prop = tuple(raw_prop)
        elif isinstance(raw_prop, set):
            prop = frozenset(raw_prop)
        elif isinstance(raw_prop, dict):
            prop = tuple(sorted(raw_prop.items()))

        try:
            hash(prop)
        except TypeError:
            raise ValueError(f"Unable to convert '{raw_prop}' of type {type(raw_prop)} to a hashable type")

        assert isinstance(prop, Hashable)

        return prop
