from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import AliasChoices, AliasGenerator, BaseModel, Field, field_serializer, field_validator
from pydantic.alias_generators import to_camel
from pydantic_extra_types.color import Color, ColorType

from .node_size import RealNumber
from .options import CaptionAlignment

NodeIdType = Union[str, int]


def create_aliases(field_name: str) -> AliasChoices:
    valid_names = [field_name]

    if field_name == "id":
        valid_names.extend(["nodeid", "node_id"])

    choices = [[choice, choice.upper(), to_camel(choice)] for choice in valid_names]

    return AliasChoices(*[alias for aliases in choices for alias in aliases])


class Node(
    BaseModel,
    extra="forbid",
    alias_generator=AliasGenerator(
        validation_alias=create_aliases,
        serialization_alias=lambda field_name: to_camel(field_name),
    ),
    validate_assignment=True,
):
    """
    A node in a graph to visualize.

    Each field is case-insensitive for input, and camelCase is also accepted.
    For example, "CAPTION_ALIGN", "captionAlign" are also valid inputs keys for the `caption_align` field.
    Upon construction however, the field names are converted to snake_case.

    For more info on each field, see the NVL library docs: https://neo4j.com/docs/nvl/current/base-library/#_nodes
    """

    #: Unique identifier for the node
    id: NodeIdType = Field(description="Unique identifier for the node")
    #: The caption of the node
    caption: Optional[str] = Field(None, description="The caption of the node")
    #: The alignment of the caption text
    caption_align: Optional[CaptionAlignment] = Field(None, description="The alignment of the caption text")
    #: The size of the caption text. The font size to node radius ratio
    caption_size: Optional[int] = Field(
        None,
        ge=1,
        le=3,
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
    #: Additional properties of the node that do not directly impact the visualization
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional properties of the node that do not directly impact the visualization",
    )

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

    @staticmethod
    def basic_fields_validation_aliases() -> set[str]:
        mandatory_fields = ["id"]
        by_field = [v.validation_alias.choices for k, v in Node.model_fields.items() if k in mandatory_fields]  # type: ignore

        return {str(alias) for aliases in by_field for alias in aliases}
