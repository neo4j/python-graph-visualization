from __future__ import annotations

import warnings
from collections.abc import Hashable, Iterable
from typing import Any, Callable, Protocol

from pydantic.alias_generators import to_snake
from pydantic_extra_types.color import Color, ColorType

from .colors import NEO4J_COLORS_CONTINUOUS, NEO4J_COLORS_DISCRETE, ColorSpace, ColorsType
from .node import Node, NodeIdType
from .node_size import RealNumber, verify_radii
from .relationship import Relationship


class EntityHost(Protocol):
    """The interface a host must expose to be driven by `GraphEntityOperations`."""

    nodes: list[Node]
    relationships: list[Relationship]

    def _sync_entities(self, *, nodes: bool = ..., relationships: bool = ...) -> None: ...


class GraphEntityOperations:
    """Recolor, resize, caption and pin operations over a host's graph entities.

    This is a composable component: it does not own the data, but reads the `nodes` and
    `relationships` from its `host` and mutates the entities in place. After each mutation
    it calls the host's `_sync_entities` hook so the host can react (e.g. the widget pushes
    the changes to its frontend).
    """

    def __init__(self, host: EntityHost) -> None:
        self._host = host

    @property
    def nodes(self) -> list[Node]:
        return self._host.nodes

    @property
    def relationships(self) -> list[Relationship]:
        return self._host.relationships

    def toggle_nodes_pinned(self, pinned: dict[NodeIdType, bool]) -> None:
        """Pin or unpin nodes. See `VisualizationGraph.toggle_nodes_pinned` for details."""
        for node in self.nodes:
            node_pinned = pinned.get(node.id)

            if node_pinned is None:
                continue

            node.pinned = node_pinned

        self._host._sync_entities(nodes=True)

    def set_node_captions(
        self,
        *,
        field: str | None = None,
        property: str | None = None,
        override: bool = True,
    ) -> None:
        """Set node captions from a field or property. See `VisualizationGraph.set_node_captions` for details."""
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

        self._host._sync_entities(nodes=True)

    def resize_nodes(
        self,
        sizes: dict[NodeIdType, RealNumber] | None = None,
        node_radius_min_max: tuple[RealNumber, RealNumber] | None = (3, 60),
        property: str | None = None,
    ) -> None:
        """Resize nodes from explicit sizes or a property. See `VisualizationGraph.resize_nodes` for details."""
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

        self._host._sync_entities(nodes=True)

    def resize_relationships(
        self,
        widths: dict[str | int, RealNumber] | None = None,
        property: str | None = None,
    ) -> None:
        """Resize relationship widths from explicit widths or a property. See `VisualizationGraph.resize_relationships` for details."""
        if widths is not None and property is not None:
            raise ValueError("At most one of the arguments `widths` and `property` can be provided")

        if widths is None and property is None:
            raise ValueError("At least one of `widths` or `property` must be given")

        # Gather relationship widths
        all_widths = {}
        if widths is not None:
            for rel in self.relationships:
                width = widths.get(rel.id, rel.width)
                if width is not None:
                    all_widths[rel.id] = width
        elif property is not None:
            for rel in self.relationships:
                width = rel.properties.get(property, rel.width)
                if width is not None:
                    all_widths[rel.id] = width

        # Validate and apply relationship widths
        for rel in self.relationships:
            width = all_widths.get(rel.id)

            if width is None:
                continue

            if not isinstance(width, (int, float)):
                raise ValueError(f"Width for relationship '{rel.id}' must be a real number, but was {width}")

            if width <= 0:
                raise ValueError(f"Width for relationship '{rel.id}' must be positive, but was {width}")

            rel.width = width

        self._host._sync_entities(relationships=True)

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
        field: str | None = None,
        property: str | None = None,
        colors: ColorsType | None = None,
        color_space: ColorSpace = ColorSpace.DISCRETE,
        override: bool = True,
    ) -> None:
        """Color nodes by a field or property (discrete or continuous). See `VisualizationGraph.color_nodes` for details."""
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
            self._color_items_dict(self.nodes, colors, override, node_to_attr)
        else:
            self._color_items_iter(self.nodes, attribute, colors, override, node_to_attr)

        self._host._sync_entities(nodes=True)

    def color_relationships(
        self,
        *,
        field: str | None = None,
        property: str | None = None,
        colors: ColorsType | None = None,
        color_space: ColorSpace = ColorSpace.DISCRETE,
        override: bool = True,
    ) -> None:
        """Color relationships by a field or property (discrete or continuous). See `VisualizationGraph.color_relationships` for details."""
        if not ((field is None) ^ (property is None)):
            raise ValueError(
                f"Exactly one of the arguments `field` (received '{field}') and `property` (received '{property}') must be provided"
            )

        if field is None:
            assert property is not None
            attribute = property

            def rel_to_attr(rel: Relationship) -> Any:
                return rel.properties.get(attribute)

        else:
            assert field is not None
            attribute = to_snake(field)

            def rel_to_attr(rel: Relationship) -> Any:
                return getattr(rel, attribute)

        if color_space == ColorSpace.DISCRETE:
            if colors is None:
                colors = NEO4J_COLORS_DISCRETE
        else:
            rel_map = {rel.id: rel_to_attr(rel) for rel in self.relationships if rel_to_attr(rel) is not None}
            normalized_map = self._normalize_values(rel_map)

            if colors is None:
                colors = NEO4J_COLORS_CONTINUOUS

            if not isinstance(colors, list):
                raise ValueError("For continuous properties, `colors` must be a list of colors representing a range")

            num_colors = len(colors)
            colors = {
                rel_to_attr(rel): colors[round(normalized_map[rel.id] * (num_colors - 1))]
                for rel in self.relationships
                if rel_to_attr(rel) is not None
            }

        if isinstance(colors, dict):
            self._color_items_dict(self.relationships, colors, override, rel_to_attr)
        else:
            self._color_items_iter(self.relationships, attribute, colors, override, rel_to_attr)

        self._host._sync_entities(relationships=True)

    def _color_items_dict(
        self,
        items: list[Node] | list[Relationship],
        colors: dict[Hashable, ColorType],
        override: bool,
        item_to_attr: Callable[[Any], Any],
    ) -> None:
        for item in items:
            color = colors.get(item_to_attr(item))

            if color is None:
                continue

            if item.color is not None and not override:
                continue

            if not isinstance(color, Color):
                item.color = Color(color)
            else:
                item.color = color

    def _color_items_iter(
        self,
        items: list[Node] | list[Relationship],
        attribute: str,
        colors: Iterable[ColorType],
        override: bool,
        item_to_attr: Callable[[Any], Any],
    ) -> None:
        exhausted_colors = False
        prop_to_color = {}
        colors_iter = iter(colors)
        for item in items:
            raw_prop = item_to_attr(item)
            try:
                prop = self._make_hashable(raw_prop)
            except ValueError:
                item_type = "nodes" if isinstance(item, Node) else "relationships"
                raise ValueError(f"Unable to color {item_type} by unhashable property type '{type(raw_prop)}'")

            if prop not in prop_to_color:
                next_color = next(colors_iter, None)
                if next_color is None:
                    exhausted_colors = True
                    colors_iter = iter(colors)
                    next_color = next(colors_iter)
                prop_to_color[prop] = next_color

            color = prop_to_color[prop]

            if item.color is not None and not override:
                continue

            if not isinstance(color, Color):
                item.color = Color(color)
            else:
                item.color = color

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
