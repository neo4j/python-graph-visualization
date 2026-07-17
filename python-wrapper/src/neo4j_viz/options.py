from __future__ import annotations

import warnings
from enum import Enum
from typing import Any, Literal, Optional, Union

import enum_tools.documentation
from pydantic import BaseModel, Field, ValidationError, model_validator
from pydantic.alias_generators import to_camel

from .colors import ColorSpace


@enum_tools.documentation.document_enum
class CaptionAlignment(str, Enum):
    """
    The alignment of the caption text for nodes and relationships.
    """

    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"


@enum_tools.documentation.document_enum
class Layout(str, Enum):
    FORCE_DIRECTED = "forcedirected"
    """
    The force-directed layout uses a physics simulation to position the nodes.
    """
    HIERARCHICAL = "hierarchical"
    """
    The nodes are then arranged by the directionality of their relationships
    """
    COORDINATE = "free"
    """
    The coordinate layout sets the position of each node based on the `x` and `y` properties of the node.
    """
    GRID = "grid"
    """
    A basic circular layout.
    """
    CIRCULAR = "circular"


@enum_tools.documentation.document_enum
class Direction(str, Enum):
    """
    The direction in which the layout should be oriented
    """

    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"


@enum_tools.documentation.document_enum
class Packing(str, Enum):
    """
    The packing method to be used
    """

    BIN = "bin"
    STACK = "stack"


class HierarchicalLayoutOptions(BaseModel, extra="forbid"):
    """
    The options for the hierarchical layout.
    """

    direction: Optional[Direction] = None
    packaging: Optional[Packing] = None


class ForceDirectedLayoutOptions(BaseModel, extra="forbid"):
    """
    The options for the force-directed layout.
    """

    gravity: Optional[float] = None
    simulationStopVelocity: Optional[float] = None


LayoutOptions = Union[HierarchicalLayoutOptions, ForceDirectedLayoutOptions]


def construct_layout_options(layout: Layout, options: dict[str, Any]) -> Optional[LayoutOptions]:
    if not options:
        return None

    if layout == Layout.FORCE_DIRECTED:
        try:
            return ForceDirectedLayoutOptions(**options)
        except ValidationError as e:
            _parse_validation_error(e, ForceDirectedLayoutOptions)
    elif layout == Layout.HIERARCHICAL:
        try:
            return HierarchicalLayoutOptions(**options)
        except ValidationError as e:
            _parse_validation_error(e, HierarchicalLayoutOptions)

    raise ValueError(
        f"Layout options only supported for layouts `{Layout.FORCE_DIRECTED}` and `{Layout.HIERARCHICAL}`, but was `{layout}`"
    )


@enum_tools.documentation.document_enum
class Renderer(str, Enum):
    """
    The renderer used to render the visualization.
    """

    WEB_GL = "webgl"
    """
    The WebGL renderer is optimized for performance and handles large graphs better.
    However, it does not render text, icons, and arrowheads on relationships.
    """
    CANVAS = "canvas"
    """
    The canvas renderer has worse performance than the WebGL renderer, so is less well suited to render large graphs.
    However, it can render text, icons, and arrowheads on relationships.
    """

    @classmethod
    def check(self, renderer: Renderer, num_nodes: int) -> None:
        if renderer == Renderer.CANVAS and num_nodes > 10_000:
            warnings.warn(
                "To visualize more than 10.000 nodes, we recommend using the WebGL renderer "
                "instead of the canvas renderer for better performance. You can set the renderer "
                "using the `renderer` parameter"
            )
        if renderer == Renderer.WEB_GL:
            warnings.warn(
                "Although better for performance, the WebGL renderer cannot render text, icons "
                "and arrowheads on relationships. If you need these features, use the canvas renderer "
                "by setting the `renderer` parameter"
            )


@enum_tools.documentation.document_enum
class SelectionMode(str, Enum):
    """
    The selection mode (a.k.a. gesture) that determines how dragging on the canvas behaves.
    """

    PAN = "single"
    """
    Drag the canvas to pan around the graph; click to select individual nodes and relationships.
    This is the default. (Shown as "Individual" in the widget UI.)
    """
    BOX = "box"
    """
    Drag to draw a rectangular region that selects all nodes and relationships within it.
    """
    LASSO = "lasso"
    """
    Drag to draw a freehand region that selects all nodes and relationships within it.
    """


@enum_tools.documentation.document_enum
class WidgetLayout(str, Enum):
    """The layout values in the JS/NVL wire format, as stored in :class:`WidgetOptions`."""

    D3_FORCE = "d3Force"
    HIERARCHICAL = "hierarchical"
    FREE = "free"
    GRID = "grid"
    CIRCULAR = "circular"


# Maps the Python-facing `Layout` to the JS/NVL wire format stored in `WidgetOptions`.
_LAYOUT_TO_JS: dict[Layout, WidgetLayout] = {
    Layout.FORCE_DIRECTED: WidgetLayout.D3_FORCE,
    Layout.HIERARCHICAL: WidgetLayout.HIERARCHICAL,
    Layout.COORDINATE: WidgetLayout.FREE,
    Layout.GRID: WidgetLayout.GRID,
    Layout.CIRCULAR: WidgetLayout.CIRCULAR,
}


class PanPosition(BaseModel):
    """The ``{x, y}`` pan position."""

    x: float
    y: float


# Mirrors the GraphSelection type in js-applet/src/graph-widget.tsx. Field names match the
# frontend wire format (`nodeIds`, `relationshipIds`) verbatim.
class GraphSelection(BaseModel):
    """The IDs of the nodes and relationships currently selected in the ``GraphWidget`` UI."""

    nodeIds: list[str] = Field(default_factory=list)
    relationshipIds: list[str] = Field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        """Serialize to the dict the frontend consumes."""
        return self.model_dump(mode="json")


DoubleClickKind = Literal["node", "relationship"]


# Mirrors the DoubleClickEvent type in js-applet/src/graph-widget.tsx. Field names match the
# frontend wire format verbatim.
class DoubleClickEvent(BaseModel):
    """A double-click on a node or relationship in the ``GraphWidget`` UI.

    Held by ``GraphWidget.last_double_click``, which is ``None`` until the first double-click. The
    ``id`` is a string, so match it against ``str(node.id)`` / ``str(relationship.id)`` to recover
    the entity.
    """

    kind: DoubleClickKind
    id: str

    def to_json(self) -> dict[str, Any]:
        """Serialize to the dict the frontend consumes."""
        return self.model_dump(mode="json")


# Mirrors the LegendEntry/LegendSection/LegendData types in js-applet/src/legend.tsx
class LegendEntry(
    BaseModel,
    alias_generator=to_camel,
    populate_by_name=True,
    serialize_by_alias=True,
):
    """A single discrete legend color box: a label and the (long-form hex) color it maps to."""

    label: str
    color: str


class LegendSection(
    BaseModel,
    alias_generator=to_camel,
    populate_by_name=True,
    serialize_by_alias=True,
):
    title: Optional[str] = None


class DiscreteLegendSection(LegendSection):
    """Legend for a discrete coloring: one color box per unique field/property value."""

    color_space: Literal[ColorSpace.DISCRETE] = ColorSpace.DISCRETE
    entries: list[LegendEntry] = Field(default_factory=list)


class ContinuousLegendSection(LegendSection):
    """Legend for a continuous coloring: a color gradient spanning the value range."""

    color_space: Literal[ColorSpace.CONTINUOUS] = ColorSpace.CONTINUOUS
    gradient: list[str] = Field(default_factory=list)
    min_value: Optional[str] = None
    max_value: Optional[str] = None


class Legend(
    BaseModel,
    alias_generator=to_camel,
    populate_by_name=True,
    serialize_by_alias=True,
):
    """The node and relationship color legend shown as an overlay in the visualization."""

    nodes: Optional[Union[DiscreteLegendSection, ContinuousLegendSection]] = Field(
        default=None, discriminator="color_space"
    )
    relationships: Optional[Union[DiscreteLegendSection, ContinuousLegendSection]] = Field(
        default=None, discriminator="color_space"
    )
    visible: bool = True

    def to_json(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


# Fields are snake_case in Python; pydantic serializes them to the camelCase keys the
# frontend's Partial<NvlOptions> expects (and accepts either casing on input). The frontend
# has many more fields, so extra="allow" lets other keys round-trip unchanged.
class NvlOptions(
    BaseModel,
    extra="allow",
    alias_generator=to_camel,
    populate_by_name=True,
    serialize_by_alias=True,
):
    """The subset of NVL instance options set from Python, nested under ``nvl_options``."""

    # ``to_camel("disable_web_gl")`` would yield ``disableWebGl``; NVL expects ``disableWebGL``.
    disable_web_gl: Optional[bool] = Field(None, alias="disableWebGL")
    min_zoom: Optional[float] = None
    max_zoom: Optional[float] = None
    allow_dynamic_min_zoom: Optional[bool] = None


# Mirrors the GraphOptions type in js-applet/src/graph-widget.tsx and is the structure stored
# in GraphWidget.options. Fields are snake_case in Python; pydantic serializes them to the
# camelCase wire format the frontend expects (and accepts either casing on input).
class WidgetOptions(
    BaseModel,
    extra="allow",
    alias_generator=to_camel,
    populate_by_name=True,
    serialize_by_alias=True,
):
    """The render options consumed by the ``GraphWidget``."""

    layout: Optional[WidgetLayout] = None
    layout_options: Optional[dict[str, Any]] = None
    nvl_options: Optional[NvlOptions] = None
    zoom: Optional[float] = None
    pan: Optional[PanPosition] = None
    show_layout_button: Optional[bool] = None
    selection_mode: Optional[SelectionMode] = None

    def to_json(self) -> dict[str, Any]:
        """Serialize to the camelCase dict the frontend consumes, dropping unset fields."""
        # mode="json" renders the `WidgetLayout`/`SelectionMode` enums as their string values.
        return self.model_dump(mode="json", exclude_none=True)


class RenderOptions(BaseModel, extra="allow"):
    """
    Options as documented at https://neo4j.com/docs/nvl/current/base-library/#_options
    """

    layout: Optional[Layout] = None
    layout_options: Optional[Union[HierarchicalLayoutOptions, ForceDirectedLayoutOptions]] = Field(
        None, serialization_alias="layoutOptions"
    )
    renderer: Optional[Renderer] = None

    pan_X: Optional[float] = Field(None, serialization_alias="panX")
    pan_Y: Optional[float] = Field(None, serialization_alias="panY")

    initial_zoom: Optional[float] = Field(None, serialization_alias="initialZoom", description="The initial zoom level")
    max_zoom: Optional[float] = Field(
        None, serialization_alias="maxZoom", description="The maximum zoom level allowed."
    )
    min_zoom: Optional[float] = Field(None, serialization_alias="minZoom", description="The minimum zoom level allowed")
    allow_dynamic_min_zoom: Optional[bool] = Field(None, serialization_alias="allowDynamicMinZoom")

    selection_mode: Optional[SelectionMode] = Field(None, serialization_alias="selectionMode")

    show_layout_button: bool = False

    @model_validator(mode="after")
    def check_layout_options_match(self) -> RenderOptions:
        if self.layout_options is None:
            return self

        if self.layout == Layout.HIERARCHICAL and not isinstance(self.layout_options, HierarchicalLayoutOptions):
            raise ValueError("layout_options must be of type HierarchicalLayoutOptions for hierarchical layout")
        if self.layout == Layout.FORCE_DIRECTED and not isinstance(self.layout_options, ForceDirectedLayoutOptions):
            raise ValueError("layout_options must be of type ForceDirectedLayoutOptions for force-directed layout")
        return self

    def to_widget_options(self) -> WidgetOptions:
        result = WidgetOptions()

        if self.layout is not None:
            result.layout = _LAYOUT_TO_JS[self.layout]

        if self.selection_mode is not None:
            result.selection_mode = self.selection_mode

        if self.layout_options is not None:
            result.layout_options = self.layout_options.model_dump(exclude_none=True)

        nvl_options = NvlOptions()
        if self.renderer is not None:
            nvl_options.disable_web_gl = self.renderer != Renderer.WEB_GL
        if self.min_zoom is not None:
            nvl_options.min_zoom = self.min_zoom
        if self.max_zoom is not None:
            nvl_options.max_zoom = self.max_zoom
        if self.allow_dynamic_min_zoom is not None:
            nvl_options.allow_dynamic_min_zoom = self.allow_dynamic_min_zoom

        # check if any nvl options are set
        if nvl_options.model_dump(exclude_none=True):
            result.nvl_options = nvl_options

        if self.initial_zoom is not None:
            result.zoom = self.initial_zoom

        if self.pan_X is not None or self.pan_Y is not None:
            result.pan = PanPosition(x=self.pan_X or 0, y=self.pan_Y or 0)

        result.show_layout_button = self.show_layout_button

        return result


def _parse_validation_error(e: ValidationError, entity_type: type[BaseModel]) -> None:
    for err in e.errors():
        loc = err["loc"][0]
        if err["type"] == "missing":
            raise ValueError(
                f"Mandatory `{entity_type.__name__}` parameter '{loc}' is missing. Expected one of {entity_type.model_fields[loc].validation_alias.choices} to be present"  # type: ignore
            )
        elif err["type"] == "extra_forbidden":
            raise ValueError(
                f"Unexpected `{entity_type.__name__}` parameter '{loc}' with provided input '{err['input']}'. "
                f"Allowed parameters are: {', '.join(entity_type.model_fields.keys())}"
            )
        else:
            raise ValueError(
                f"Error for `{entity_type.__name__}` parameter '{loc}' with provided input '{err['input']}'. Reason: {err['msg']}"
            )
