from __future__ import annotations

from functools import cached_property
from typing import Any, Literal

from IPython.display import HTML

from ._graph_entity_operations import GraphEntityOperations, delegate_doc
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
    ) -> RenderOptions:
        """Shared validation + option building for render / render_widget."""
        num_nodes = len(self.nodes)
        if num_nodes > max_allowed_nodes:
            raise ValueError(
                f"Too many nodes ({num_nodes}) to render. Maximum allowed nodes is set "
                f"to {max_allowed_nodes} for performance reasons. It can be increased by "
                "overriding `max_allowed_nodes`, but rendering could then take a long time"
            )

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
        )

        return GraphWidget.from_graph_data(
            self.nodes,
            self.relationships,
            width=width,
            height=height,
            options=render_options,
            theme=theme,
        )
