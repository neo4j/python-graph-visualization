from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .node import Node
from .relationship import Relationship

# Only data URIs at least this long are worth factoring: below it, a reference is
# not much smaller than the value, and names/URLs are already short.
_MIN_FACTORED_LENGTH = 256

_REF_PREFIX = "#"


def _icon_values(entity: Node | Relationship) -> Iterator[str]:
    if isinstance(entity, Node) and entity.icon is not None:
        yield entity.icon

    if entity.overlay_icon is not None:
        yield entity.overlay_icon.url


def build_icon_refs(nodes: list[Node], relationships: list[Relationship]) -> tuple[dict[str, str], dict[str, str]]:
    """Factor long data-URI icons into a shared table.

    Returns ``(refs, uri_to_ref)``: ``refs`` maps a short reference (``#0``, ``#1``, ...) to its
    data URI and is synced to the frontend once; ``uri_to_ref`` maps a data URI back to its
    reference and is used while serializing entities. The assignment is deterministic for a given
    set of entities, so it stays consistent between the table and the serialized entities.
    """
    refs: dict[str, str] = {}
    uri_to_ref: dict[str, str] = {}

    entities: list[Node | Relationship] = [*nodes, *relationships]
    for entity in entities:
        for value in _icon_values(entity):
            if value in uri_to_ref:
                continue
            if not value.startswith("data:") or len(value) < _MIN_FACTORED_LENGTH:
                continue

            ref = f"{_REF_PREFIX}{len(refs)}"
            refs[ref] = value
            uri_to_ref[value] = ref

    return refs, uri_to_ref


def apply_icon_refs(entity_dict: dict[str, Any], uri_to_ref: dict[str, str]) -> dict[str, Any]:
    """Replace factored icon values in a serialized entity with their short references."""
    icon = entity_dict.get("icon")
    if isinstance(icon, str) and icon in uri_to_ref:
        entity_dict["icon"] = uri_to_ref[icon]

    overlay_icon = entity_dict.get("overlayIcon")
    if isinstance(overlay_icon, dict):
        url = overlay_icon.get("url")
        if isinstance(url, str) and url in uri_to_ref:
            overlay_icon["url"] = uri_to_ref[url]

    return entity_dict
