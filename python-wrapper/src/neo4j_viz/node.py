from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import AliasChoices, BaseModel, Field, field_serializer, field_validator
from pydantic_extra_types.color import Color, ColorType

from .node_size import RealNumber
from .options import CaptionAlignment

NodeIdType = Union[str, int]


class Node(BaseModel, extra="allow"):
    """
    A node in a graph to visualize.
    All options available in the NVL library (see https://neo4j.com/docs/nvl/current/base-library/#_nodes)
    """

    #: Unique identifier for the node
    id: NodeIdType = Field(
        validation_alias=AliasChoices("id", "nodeId", "node_id"), description="Unique identifier for the node"
    )
    #: The caption of the node
    caption: Optional[str] = Field(None, description="The caption of the node")
    #: The alignment of the caption text
    caption_align: Optional[CaptionAlignment] = Field(
        None, serialization_alias="captionAlign", description="The alignment of the caption text"
    )
    #: The size of the caption text. The font size to node radius ratio
    caption_size: Optional[int] = Field(
        None,
        ge=1,
        le=3,
        serialization_alias="captionSize",
        description="The size of the caption text. The font size to node radius ratio",
    )
    #: The size of the node as radius in pixel
    size: Optional[RealNumber] = Field(None, ge=0, description="The size of the node as radius in pixel")
    #: The color of the node. Allowed input is for example "#FF0000", "red" or (255, 0, 0)
    color: Optional[ColorType] = Field(None, description="The color of the node")
    #: Whether the node is pinned in the visualization
    pinned: Optional[bool] = Field(None, description="Whether the node is pinned in the visualization")
    #: The x-coordinate of the node
    x: Optional[RealNumber] = Field(None, description="The x-coordinate of the node")
    #: The y-coordinate of the node
    y: Optional[RealNumber] = Field(None, description="The y-coordinate of the node")
    #: The properties of the node
    properties: dict[str, Any] = Field(default_factory=dict, description="The properties of the node")

    @field_serializer("color")
    def serialize_color(self, color: Color) -> str:
        return color.as_hex(format="long")

    @field_serializer("id")
    def serialize_id(self, id: Union[str, int]) -> str:
        return str(id)

    @field_validator("color")
    @classmethod
    def cast_color(cls, color: ColorType) -> Color:
        if not isinstance(color, Color):
            return Color(color)

        return color

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True, by_alias=True)
