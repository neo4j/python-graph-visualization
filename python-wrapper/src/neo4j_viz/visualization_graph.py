from __future__ import annotations

from functools import cached_property
from typing import Any, Literal

from IPython.display import HTML

from ._graph_entity_operations import GraphEntityOperations
from ._validation import OnDangling, check_dangling_relationships
from .colors import ColorSpace, ColorsType
from .node import Node, NodeIdType
from .node_size import RealNumber
from .nvl import NVL
from .options import (
    Layout,
    LayoutOptions,
    Renderer,
    RenderOptions,
    construct_layout_options,
)
from .relationship import Relationship
from .widget import GraphWidget


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

    def __str__(self) -> str:
        return f"VisualizationGraph(nodes={len(self.nodes)}, relationships={len(self.relationships)})"

    @cached_property
    def _entity_ops(self) -> GraphEntityOperations:
        return GraphEntityOperations(self)

    def _sync_entities(self, *, nodes: bool = False, relationships: bool = False) -> None:
        """Hook invoked after entities are mutated in place. A no-op for a plain graph."""

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
        Given a VisualizationGraph `VG`:

        >>> nodes = [
        ...    Node(id="0", properties={"name": "Alice", "age": 30}),
        ...    Node(id="1", properties={"name": "Bob", "age": 25}),
        ... ]
        >>> VG = VisualizationGraph(nodes=nodes, relationships=[])

        Set node captions from a property:

        >>> VG.set_node_captions(property="name")

        Set node captions from a field, only if not already set:

        >>> VG.set_node_captions(field="id", override=False)
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

        Given a VisualizationGraph `VG`:

        >>> nodes = [
        ...    Node(id="0", properties={"label": "Person", "score": 10}),
        ...    Node(id="1", properties={"label": "Person", "score": 20}),
        ... ]
        >>> VG = VisualizationGraph(nodes=nodes, relationships=[])

        Color nodes based on a discrete field such as "label":

        >>> VG.color_nodes(field="label", color_space=ColorSpace.DISCRETE)

        Color nodes based on a continuous field such as "score":

        >>> VG.color_nodes(field="score", color_space=ColorSpace.CONTINUOUS)

        Color nodes based on a custom colors such as from palettable:

        >>> from palettable.wesanderson import Moonrise1_5  # type: ignore[import-untyped]
        >>> VG.color_nodes(field="label", colors=Moonrise1_5.colors)
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

        Given a VisualizationGraph `VG`:

        >>> nodes = [Node(id="0"), Node(id="1")]
        >>> relationships = [
        ...    Relationship(source="0", target="1", caption="ACTED_IN", properties={"score": 10}),
        ...    Relationship(source="1", target="0", caption="DIRECTED", properties={"score": 20}),
        ... ]
        >>> VG = VisualizationGraph(nodes=nodes, relationships=relationships)

        Color relationships based on a discrete field such as "caption":

        >>> VG.color_relationships(field="caption", color_space=ColorSpace.DISCRETE)

        Color relationships based on a continuous field such as "score":

        >>> VG.color_relationships(property="score", color_space=ColorSpace.CONTINUOUS)
        """
        self._entity_ops.color_relationships(
            field=field, property=property, colors=colors, color_space=color_space, override=override
        )

    def _build_render_options(
        self,
        layout: Layout | str | None,
        layout_options: dict[str, Any] | LayoutOptions | None,
        renderer: Renderer | str,
        pan_position: tuple[float, float] | None,
        initial_zoom: float | None,
        min_zoom: float,
        max_zoom: float,
        allow_dynamic_min_zoom: bool,
        max_allowed_nodes: int,
        show_layout_button: bool,
        on_dangling: OnDangling,
    ) -> RenderOptions:
        """Shared validation + option building for render / render_widget."""
        num_nodes = len(self.nodes)
        if num_nodes > max_allowed_nodes:
            raise ValueError(
                f"Too many nodes ({num_nodes}) to render. Maximum allowed nodes is set "
                f"to {max_allowed_nodes} for performance reasons. It can be increased by "
                "overriding `max_allowed_nodes`, but rendering could then take a long time"
            )

        check_dangling_relationships(self.nodes, self.relationships, on_dangling)

        if isinstance(renderer, str):
            renderer = Renderer(renderer)

        Renderer.check(renderer, num_nodes)

        if not layout:
            layout = Layout.FORCE_DIRECTED
        if isinstance(layout, str):
            layout = Layout(layout.lower())
        if not layout_options:
            layout_options = {}

        if isinstance(layout_options, dict):
            layout_options_typed = construct_layout_options(layout, layout_options)
        else:
            layout_options_typed = layout_options

        return RenderOptions(
            layout=layout,
            layout_options=layout_options_typed,
            renderer=renderer,
            pan_X=pan_position[0] if pan_position is not None else None,
            pan_Y=pan_position[1] if pan_position is not None else None,
            initial_zoom=initial_zoom,
            min_zoom=min_zoom,
            max_zoom=max_zoom,
            allow_dynamic_min_zoom=allow_dynamic_min_zoom,
            show_layout_button=show_layout_button,
        )

    def render(
        self,
        layout: Layout | str | None = None,
        layout_options: dict[str, Any] | LayoutOptions | None = None,
        renderer: Renderer | str = Renderer.CANVAS,
        width: str = "100%",
        height: str = "600px",
        pan_position: tuple[float, float] | None = None,
        initial_zoom: float | None = None,
        min_zoom: float = 0.075,
        max_zoom: float = 10,
        allow_dynamic_min_zoom: bool = True,
        max_allowed_nodes: int = 10_000,
        theme: Literal["auto"] | Literal["light"] | Literal["dark"] = "auto",
        on_dangling: OnDangling = "warn",
    ) -> HTML:
        """
        Render the graph as an HTML object.

        Returns an :class:`IPython.display.HTML` object that will be displayed in environments
        that support HTML rendering, such as Jupyter notebooks or Streamlit applications.

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
        theme:
            The theme of the rendered graph. Can be 'auto', 'light', or 'dark'
        on_dangling:
            What to do when a relationship references a node id that is not in the graph . One of "warn" (default), "error", or "none".

        Example
        -------
        Basic rendering of a VisualizationGraph:
        >>> from neo4j_viz import Node, Relationship, VisualizationGraph
        """
        render_options = self._build_render_options(
            layout,
            layout_options,
            renderer,
            pan_position,
            initial_zoom,
            min_zoom,
            max_zoom,
            allow_dynamic_min_zoom,
            max_allowed_nodes,
            show_layout_button=False,  # The button only works with the widget
            on_dangling=on_dangling,
        )

        return NVL().render(
            self.nodes,
            self.relationships,
            render_options,
            width,
            height,
            theme,
        )

    def render_widget(
        self,
        layout: Layout | str | None = None,
        layout_options: dict[str, Any] | LayoutOptions | None = None,
        renderer: Renderer | str = Renderer.CANVAS,
        width: str = "100%",
        height: str = "600px",
        pan_position: tuple[float, float] | None = None,
        initial_zoom: float | None = None,
        min_zoom: float = 0.075,
        max_zoom: float = 10,
        allow_dynamic_min_zoom: bool = True,
        max_allowed_nodes: int = 10_000,
        theme: Literal["auto"] | Literal["light"] | Literal["dark"] = "auto",
        on_dangling: OnDangling = "warn",
    ) -> GraphWidget:
        """
        Render the graph as an interactive Jupyter widget (anywidget).

        Returns a :class:`GraphWidget` that provides two-way data sync between Python
        and JavaScript. Works in JupyterLab, Notebook 7, VS Code, and Colab.

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
        theme:
            The theme to use for the rendered graph.
        on_dangling:
            What to do when a relationship references a node id that is not in the graph. One of "warn" (default), "error", or "none".
        """
        render_options = self._build_render_options(
            layout,
            layout_options,
            renderer,
            pan_position,
            initial_zoom,
            min_zoom,
            max_zoom,
            allow_dynamic_min_zoom,
            max_allowed_nodes,
            show_layout_button=True,
            on_dangling=on_dangling,
        )

        return GraphWidget.from_graph_data(
            self.nodes,
            self.relationships,
            width=width,
            height=height,
            options=render_options,
            theme=theme,
        )
