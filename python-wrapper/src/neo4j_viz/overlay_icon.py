from __future__ import annotations

from typing import Any, Optional

from pydantic import AliasChoices, AliasGenerator, BaseModel, Field, field_serializer
from pydantic.alias_generators import to_camel


def create_aliases(field_name: str) -> AliasChoices:
    choices = [[field_name, field_name.upper(), to_camel(field_name)]]

    return AliasChoices(*[alias for aliases in choices for alias in aliases])


class OverlayIcon(
    BaseModel,
    extra="forbid",
    alias_generator=AliasGenerator(
        validation_alias=create_aliases,
        serialization_alias=lambda field_name: to_camel(field_name),
    ),
    validate_assignment=True,
):
    """
    An icon drawn on top of a node or relationship.

    Each field is case-insensitive for input, and camelCase is also accepted.
    For more info, see the NVL library docs: https://neo4j.com/docs/nvl/current/base-library/#_nodes
    """

    #: The icon to display. Either the name of a built-in icon (see `Icons`) or a URL.
    #: Icons are expected to be square and black; on a dark node color the icon is inverted to white.
    url: str = Field(description="The icon to display. Either the name of a built-in icon (see `Icons`) or a URL")
    #: The position of the icon relative to the element, as a fraction of its size.
    #: `(1, 1)` is the bottom right corner and `(-1, -1)` is the top left corner. Defaults to the center.
    position: Optional[tuple[float, float]] = Field(
        None,
        description="The position of the icon relative to the element as a fraction of its size. "
        "(1, 1) is the bottom right corner and (-1, -1) the top left corner. Defaults to the center",
    )
    #: The size of the icon relative to the element size. Defaults to 1.
    size: Optional[float] = Field(
        None,
        gt=0.0,
        description="The size of the icon relative to the element size. Defaults to 1",
    )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True, by_alias=True)

    @field_serializer("position")
    def serialize_position(self, position: tuple[float, float]) -> list[float]:
        return list(position)
