from __future__ import annotations

import json
import pathlib
from functools import cached_property
from typing import Any, Callable, TypeVar, Union, cast

import anywidget
import pydantic
import traitlets

from ._graph_entity_operations import GraphEntityOperations, LegendSectionInput
from ._validation import OnDangling, OnDuplicate, check_dangling_relationships, merge_on_duplicate
from .colors import ColorSpace, ColorsType
from .node import Node, NodeIdType
from .node_size import RealNumber
from .options import (
    DoubleClickEvent,
    GraphSelection,
    Layout,
    LayoutOptions,
    Legend,
    NvlOptions,
    PanPosition,
    Renderer,
    RenderOptions,
    SelectionMode,
    WidgetOptions,
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


_ModelT = TypeVar("_ModelT", bound=pydantic.BaseModel)


class PydanticTrait(traitlets.Instance[_ModelT]):
    """A typed traitlets trait holding a pydantic model."""

    klass: type[_ModelT]

    def validate(self, obj: traitlets.HasTraits, value: Any) -> _ModelT:
        if value is not None and not isinstance(value, self.klass):
            value = self.klass.model_validate(value)
        return cast("_ModelT", super().validate(obj, value))


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
    options: PydanticTrait[WidgetOptions] = PydanticTrait(WidgetOptions, args=()).tag(
        sync=True,
        to_json=lambda value, widget: value.to_json(),
        from_json=lambda value, widget: WidgetOptions.model_validate(value),
    )
    theme: traitlets.Unicode[str, str | bytes] = traitlets.Unicode(
        default_value="auto", help="Theme of the graph widget. Can be 'auto', 'light', or 'dark'."
    ).tag(sync=True)
    selected: PydanticTrait[GraphSelection] = PydanticTrait(
        GraphSelection,
        args=(),
        help="The nodes and relationships currently selected in the widget UI, as a "
        "`GraphSelection` with `nodeIds` and `relationshipIds`. Synced two-way with the frontend.",
    ).tag(
        sync=True,
        to_json=lambda value, widget: value.to_json(),
        from_json=lambda value, widget: GraphSelection.model_validate(value),
    )
    legend: PydanticTrait[Legend] = PydanticTrait(
        Legend,
        args=(),
        help="The node and relationship color legend, a `Legend`. Populated automatically by "
        "`color_nodes`/`color_relationships` and overridable via `set_legend`. Synced to the frontend.",
    ).tag(
        sync=True,
        to_json=lambda value, widget: value.to_json(),
        from_json=lambda value, widget: Legend.model_validate(value),
    )
    last_double_click: PydanticTrait[DoubleClickEvent] = PydanticTrait(
        DoubleClickEvent,
        allow_none=True,
        default_value=None,
        help="The most recently double-clicked node or relationship in the widget UI, as a "
        "`DoubleClickEvent` with `kind` and `id`, or `None` until the first double-click. Synced "
        "from the frontend; prefer the `on_node_double_click` / `on_relationship_double_click` "
        "convenience methods.",
    ).tag(
        sync=True,
        to_json=lambda value, widget: value.to_json() if value is not None else None,
        from_json=lambda value, widget: DoubleClickEvent.model_validate(value) if value is not None else None,
    )

    _max_allowed_nodes: int = 10_000

    def on_selection_change(self, callback: Callable[[GraphSelection], None]) -> Callable[[dict[str, Any]], None]:
        """
        Register a callback that fires whenever the widget's `selected` trait changes.

        A convenience wrapper around `observe(..., names=["selected"])`: the callback receives the
        new `GraphSelection` directly, rather than a raw change dict. The selection holds the
        `nodeIds` and `relationshipIds` currently selected in the widget UI; the IDs are strings, so
        match them against `str(node.id)` / `str(relationship.id)` to recover the
        `Node`/`Relationship` objects.

        Parameters
        ----------
        callback:
            A function called with the new `GraphSelection` each time the selection changes.

        Returns
        -------
        The registered handler. Pass it to `unobserve(handler, names=["selected"])` to stop observing.

        Examples
        --------
        Given a GraphWidget `widget`:

        >>> def show(selection):
        ...     print(selection.nodeIds, selection.relationshipIds)
        >>> handler = widget.on_selection_change(show)

        Stop reacting to selection changes:

        >>> widget.unobserve(handler, names=["selected"])
        """

        def handler(change: dict[str, Any]) -> None:
            callback(change["new"])

        self.observe(handler, names=["selected"])
        return handler

    def on_node_double_click(self, callback: Callable[[Node | None], None]) -> Callable[[dict[str, Any]], None]:
        """
        Register a callback that fires whenever a node is double-clicked in the widget UI.

        The callback receives the double-clicked `Node`, resolved from the widget's current
        `nodes` by matching ids. It is `None` in the rare case the node is no longer in the graph.
        Relationship double-clicks are ignored by this callback (use `on_relationship_double_click`).

        Note that double-clicking the *same* node twice in a row fires the callback only once, since
        the underlying `last_double_click` trait does not change value. For the raw event (`kind`
        and `id`), observe the `last_double_click` trait directly instead.

        Parameters
        ----------
        callback:
            A function called with the double-clicked `Node` (or `None`).

        Returns
        -------
        The registered handler. Pass it to `unobserve(handler, names=["last_double_click"])` to stop
        observing.

        Examples
        --------
        Given a GraphWidget `widget`:

        >>> def expand(node):
        ...     print("double-clicked", node.id if node else None)
        >>> handler = widget.on_node_double_click(expand)
        """

        def handler(change: dict[str, Any]) -> None:
            event: DoubleClickEvent | None = change["new"]
            if event is None or event.kind != "node":
                return
            node = next((n for n in self.nodes if str(n.id) == event.id), None)
            callback(node)

        self.observe(handler, names=["last_double_click"])
        return handler

    def on_relationship_double_click(
        self, callback: Callable[[Relationship | None], None]
    ) -> Callable[[dict[str, Any]], None]:
        """
        Register a callback that fires whenever a relationship is double-clicked in the widget UI.

        The callback receives the double-clicked `Relationship`, resolved from the widget's current
        `relationships` by matching ids. It is `None` in the rare case the relationship is no longer
        in the graph. Node double-clicks are ignored by this callback (use `on_node_double_click`).

        Note that double-clicking the *same* relationship twice in a row fires the callback only
        once, since the underlying `last_double_click` trait does not change value. For the raw event
        (`kind` and `id`), observe the `last_double_click` trait directly instead.

        Parameters
        ----------
        callback:
            A function called with the double-clicked `Relationship` (or `None`).

        Returns
        -------
        The registered handler. Pass it to `unobserve(handler, names=["last_double_click"])` to stop
        observing.
        """

        def handler(change: dict[str, Any]) -> None:
            event: DoubleClickEvent | None = change["new"]
            if event is None or event.kind != "relationship":
                return
            relationship = next((r for r in self.relationships if str(r.id) == event.id), None)
            callback(relationship)

        self.observe(handler, names=["last_double_click"])
        return handler

    @classmethod
    def from_graph_data(
        cls,
        nodes: list[Node],
        relationships: list[Relationship],
        width: str = "100%",
        height: str = "600px",
        options: RenderOptions | None = None,
        theme: str = "auto",
        legend: Legend | None = None,
        max_allowed_nodes: int = 10_000,
    ) -> GraphWidget:
        """Create a GraphWidget from Node and Relationship lists."""
        widget = cls(
            nodes=nodes,
            relationships=relationships,
            width=width,
            height=height,
            options=options.to_widget_options() if options else WidgetOptions(),
            theme=theme,
            legend=legend if legend is not None else Legend(),
        )
        widget._max_allowed_nodes = max_allowed_nodes
        return widget

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
            field=field,
            property=property,
            colors=colors,
            color_space=color_space,
            override=override,
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
            field=field,
            property=property,
            colors=colors,
            color_space=color_space,
            override=override,
        )

    def set_legend(
        self,
        *,
        nodes: LegendSectionInput | None = None,
        relationships: LegendSectionInput | None = None,
        visible: bool = True,
    ) -> None:
        """
        Set the color legend explicitly, overriding any legend captured from `color_nodes`/`color_relationships`.

        Parameters
        ----------
        nodes:
            The node legend. Either a `LegendSection`, a `{label: color}` mapping, or an iterable of
            `LegendEntry` / `(label, color)` pairs. Left unchanged if None.
        relationships:
            The relationship legend, in the same accepted forms as `nodes`. Left unchanged if None.
        visible:
            Whether the legend overlay is shown.

        Examples
        --------
        Given a GraphWidget `widget`:

        >>> widget.set_legend(nodes={"Movies": "blue", "Directors": "red"})
        """
        self._entity_ops.set_legend(nodes=nodes, relationships=relationships, visible=visible)

    def show_legend(self, visible: bool = True) -> None:
        """
        Show or hide the color legend overlay.

        Parameters
        ----------
        visible:
            Whether the legend overlay is shown.
        """
        self._entity_ops.show_legend(visible)

    def _render_options(self) -> WidgetOptions:
        """Return a mutable copy of the current JS-shaped render options.

        Mutating and then reassigning the returned model to :attr:`options` triggers the
        traitlets change notification that syncs the new options to the frontend.
        """
        current: WidgetOptions = self.options
        return current.model_copy(deep=True)

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

        js = RenderOptions(layout=layout, layout_options=layout_options).to_widget_options()

        new = self._render_options()
        new.layout = js.layout
        new.layout_options = js.layout_options
        self.options = new

    def set_zoom(self, zoom: float) -> None:
        """
        Change the zoom level of the graph, in place.

        Parameters
        -----------
        zoom:
            The zoom level to apply.
        """
        new = self._render_options()
        new.zoom = zoom
        self.options = new

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
        new.pan = PanPosition(x=x, y=y)
        self.options = new

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
        nvl_options = new.nvl_options or NvlOptions()
        nvl_options.disable_web_gl = renderer != Renderer.WEB_GL
        new.nvl_options = nvl_options
        self.options = new

    def set_selection_mode(self, mode: SelectionMode | str) -> None:
        """
        Change the selection mode (gesture) that determines how dragging on the canvas behaves, in place.

        Parameters
        -----------
        mode:
            The selection mode to use. One of `SelectionMode.PAN` (the default, drag to pan and click to
            select individual entities), `SelectionMode.BOX` (drag a rectangle to select), or
            `SelectionMode.LASSO` (drag a freehand region to select). A string such as `"single"`, `"box"`,
            or `"lasso"` is also accepted.
        """
        if isinstance(mode, str):
            mode = SelectionMode(mode)

        new = self._render_options()
        new.selection_mode = mode
        self.options = new

    def set_show_layout_button(self, show: bool = True) -> None:
        """
        Toggle the layout selector button in the widget UI, in place.

        Parameters
        -----------
        show:
            Whether the layout button should be shown.
        """
        new = self._render_options()
        new.show_layout_button = show
        self.options = new

    def add_data(
        self,
        nodes: Node | list[Node] | None = None,
        relationships: Relationship | list[Relationship] | None = None,
        on_dangling: OnDangling = "warn",
        on_duplicate: OnDuplicate = "ignore",
    ) -> None:
        """
        Add nodes or relationships to the graph widget.

        Parameters
        -----------
        nodes:
            Nodes to add to the graph widget.
        relationships:
            Relationships to add to the graph widget.
        on_dangling:
            What to do when a resulting relationship references a node id that is not in the graph
            (which the frontend would silently render as empty). One of "warn" (default), "error",
            or "none".
        on_duplicate:
            What to do when an added node or relationship has the same id as one already in the
            graph (ids are compared as strings, and the check also de-duplicates within the added
            batch). One of "ignore" (default, keep the existing entity and drop the added
            duplicate), "replace" (swap the existing entity for the added one, keeping its
            position), or "none" (skip the check and append everything, which may leave duplicate
            ids).
        """
        if isinstance(nodes, Node):
            nodes = [nodes]
        if isinstance(relationships, Relationship):
            relationships = [relationships]

        if nodes and len(self.nodes) + len(nodes) > self._max_allowed_nodes:
            raise ValueError(
                f"Adding {len(nodes)} nodes would result in {len(self.nodes) + len(nodes)} nodes, "
                f"which exceeds the maximum of {self._max_allowed_nodes} nodes set when this widget "
                "was created. It can be increased by overriding `max_allowed_nodes` in "
                "`render_widget`, but rendering could then take a long time."
            )

        if nodes:
            self.nodes = merge_on_duplicate(self.nodes, nodes, on_duplicate)
        if relationships:
            self.relationships = merge_on_duplicate(self.relationships, relationships, on_duplicate)

        check_dangling_relationships(self.nodes, self.relationships, on_dangling)

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
        # Compare ids as strings on both sides, matching how ids are serialized for the
        # frontend (see _validation.check_dangling_relationships): ``Node(id=1)`` and a
        # request to remove ``"1"`` refer to the same node.
        if isinstance(nodes, Node):
            node_ids_to_remove = {str(nodes.id)}
        elif isinstance(nodes, NodeIdType):
            node_ids_to_remove = {str(nodes)}
        elif nodes is None:
            node_ids_to_remove = set()
        else:
            node_ids_to_remove = {str(n.id) if isinstance(n, Node) else str(n) for n in nodes}

        if isinstance(relationships, Relationship):
            rel_ids_to_remove = {str(relationships.id)}
        elif isinstance(relationships, RelationshipIdType):
            rel_ids_to_remove = {str(relationships)}
        elif relationships is None:
            rel_ids_to_remove = set()
        else:
            rel_ids_to_remove = {str(r.id) if isinstance(r, Relationship) else str(r) for r in relationships}

        if node_ids_to_remove:
            self.nodes = [n for n in self.nodes if str(n.id) not in node_ids_to_remove]

        def keep_rel(r: Relationship) -> bool:
            return (
                str(r.id) not in rel_ids_to_remove
                and str(r.source) not in node_ids_to_remove
                and str(r.target) not in node_ids_to_remove
            )

        # Run the cleanup whenever anything is being removed. A node-only delete must also
        # drop the relationships that pointed at it, otherwise the frontend silently renders
        # an empty graph (see _validation.check_dangling_relationships).
        if node_ids_to_remove or rel_ids_to_remove:
            self.relationships = [r for r in self.relationships if keep_rel(r)]
