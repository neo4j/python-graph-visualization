from __future__ import annotations

from typing import Any, Optional, Union
from uuid import uuid4

from pydantic import AliasChoices, AliasGenerator, BaseModel, Field, field_serializer, field_validator
from pydantic.alias_generators import to_camel
from pydantic_extra_types.color import Color, ColorType

from .options import CaptionAlignment


def create_aliases(field_name: str) -> AliasChoices:
    valid_names = [field_name]

    if field_name == "source":
        valid_names.extend(["sourcenodeid", "source_node_id", "from"])
    if field_name == "target":
        valid_names.extend(["targetnodeid", "target_node_id", "to"])

    choices = [[choice, choice.upper(), to_camel(choice)] for choice in valid_names]

    return AliasChoices(*[alias for aliases in choices for alias in aliases])


class Relationship(
    BaseModel,
    extra="forbid",
    alias_generator=AliasGenerator(
        validation_alias=create_aliases,
        serialization_alias=lambda field_name: to_camel(field_name),
    ),
    validate_assignment=True,
):
    """
    A relationship in a graph to visualize.

    Each field is case-insensitive for input, and camelCase is also accepted.
    For example, "CAPTION_ALIGN", "captionAlign" are also valid inputs keys for the `caption_align` field.
    Upon construction however, the field names are converted to snake_case.

    For more info on each field, see the NVL library docs: https://neo4j.com/docs/nvl/current/base-library/#_relationships
    """

    #: Unique identifier for the relationship
    id: Union[str, int] = Field(
        default_factory=lambda: uuid4().hex, description="Unique identifier for the relationship"
    )
    #: Node ID where the relationship points from
    source: Union[str, int] = Field(
        serialization_alias="from",
        description="Node ID where the relationship points from",
    )
    #: Node ID where the relationship points to
    target: Union[str, int] = Field(
        serialization_alias="to",
        description="Node ID where the relationship points to",
    )
    #: The caption of the relationship
    caption: Optional[str] = Field(None, description="The caption of the relationship")
    #: The alignment of the caption text
    caption_align: Optional[CaptionAlignment] = Field(None, description="The alignment of the caption text")
    #: The size of the caption text
    caption_size: Optional[Union[int, float]] = Field(None, gt=0.0, description="The size of the caption text")
    #: The color of the relationship. Allowed input is for example "#FF0000", "red" or (255, 0, 0)
    color: Optional[ColorType] = Field(None, description="The color of the relationship")
    #: Additional properties of the relationship that do not directly impact the visualization
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional properties of the relationship that do not directly impact the visualization",
    )

    @field_serializer("color")
    def serialize_color(self, color: Color) -> str:
        return color.as_hex(format="long")

    @field_serializer("id")
    def serialize_id(self, id: Union[str, int]) -> str:
        return str(id)

    @field_serializer("source")
    def serialize_source(self, source: Union[str, int]) -> str:
        return str(source)

    @field_serializer("target")
    def serialize_target(self, target: Union[str, int]) -> str:
        return str(target)

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
        basic_fields = ["id", "source", "target"]
        by_field = [
            v.validation_alias.choices  # type: ignore
            for k, v in Relationship.model_fields.items()
            if k in basic_fields
        ]

        return {str(alias) for aliases in by_field for alias in aliases}
