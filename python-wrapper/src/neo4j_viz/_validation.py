from __future__ import annotations

import warnings
from collections.abc import Sequence
from typing import Literal, TypeVar

from .node import Node, NodeIdType
from .relationship import Relationship

OnDangling = Literal["error", "warn", "none"]

OnDuplicate = Literal["replace", "ignore", "none"]

_Entity = TypeVar("_Entity", Node, Relationship)

# Number of offending relationships to name in the message before truncating.
_MAX_REPORTED = 5


def merge_on_duplicate(
    existing: list[_Entity],
    incoming: list[_Entity],
    on_duplicate: OnDuplicate,
) -> list[_Entity]:
    """Merge ``incoming`` entities into ``existing``, resolving id collisions per ``on_duplicate``.

    Duplicates are detected by id, compared as strings to match how ids are serialized for the
    frontend (so e.g. ``Node(id=1)`` and ``Node(id="1")`` collide). The check also de-duplicates
    ids *within* ``incoming``.

    Parameters
    ----------
    existing:
        The entities already in the graph.
    incoming:
        The entities being added.
    on_duplicate:
        How to resolve an incoming entity whose id already exists: ``"replace"`` swaps the existing
        entity for the incoming one (keeping the existing position); ``"ignore"`` keeps the existing
        entity and drops the incoming duplicate; ``"none"`` skips the check and appends everything,
        which may leave duplicate ids in the graph.
    """
    if on_duplicate == "none":
        return existing + incoming

    if on_duplicate not in ("replace", "ignore"):
        raise ValueError(f"Invalid `on_duplicate` value {on_duplicate!r}. Expected 'replace', 'ignore', or 'none'.")

    existing_ids = {str(e.id) for e in existing}

    if on_duplicate == "replace":
        # Last occurrence wins within `incoming`; replace matching existing entries in place.
        incoming_by_id = {str(item.id): item for item in incoming}
        result = [incoming_by_id.get(str(e.id), e) for e in existing]
        # Append genuinely new ids, in first-seen order, using their last-wins value.
        for key in dict.fromkeys(str(item.id) for item in incoming):
            if key not in existing_ids:
                result.append(incoming_by_id[key])
        return result

    # on_duplicate == "ignore": keep existing (and the first incoming for brand-new ids).
    result = list(existing)
    seen = set(existing_ids)
    for item in incoming:
        key = str(item.id)
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result


def check_dangling_relationships(
    nodes: list[Node],
    relationships: list[Relationship],
    on_dangling: OnDangling = "warn",
) -> None:
    """Check for relationships referencing node ids that are not in ``nodes``.

    The frontend silently renders an empty graph when a relationship's ``source`` or ``target``
    is missing from the nodes, so by default we surface this as a warning. Node and relationship
    ids are compared as strings, matching how they are serialized for the frontend (so e.g.
    ``Node(id=1)`` and ``Relationship(source="1")`` are considered to match).

    Parameters
    ----------
    nodes:
        The nodes in the graph.
    relationships:
        The relationships to check against ``nodes``.
    on_dangling:
        What to do when a dangling relationship is found: ``"warn"`` (default) emits a warning,
        ``"error"`` raises a ``ValueError``, and ``"none"`` skips the check entirely.
    """
    if on_dangling == "none":
        return

    node_ids = {str(node.id) for node in nodes}
    dangling = [rel for rel in relationships if str(rel.source) not in node_ids or str(rel.target) not in node_ids]
    if not dangling:
        return

    examples = []
    for rel in dangling[:_MAX_REPORTED]:
        missing = [str(end) for end in (rel.source, rel.target) if str(end) not in node_ids]
        examples.append(f"relationship {rel.id!r} (source={rel.source!r}, target={rel.target!r}) -> missing {missing}")
    if len(dangling) > _MAX_REPORTED:
        examples.append(f"... and {len(dangling) - _MAX_REPORTED} more")

    message = (
        f"{len(dangling)} relationship(s) reference node ids that are not in the graph, "
        "so they will not be drawn:\n  " + "\n  ".join(examples) + "\n"
        "Add the missing nodes, or pass `on_dangling='none'` to silence this. "
        "Pass `on_dangling='error'` to raise instead."
    )

    if on_dangling == "error":
        raise ValueError(message)
    warnings.warn(message)


def resolve_fit_node_ids(node_ids: Sequence[NodeIdType] | None, nodes: Sequence[Node]) -> list[str] | None:
    """Validate the node ids to frame and normalize them to the strings the frontend matches.

    Returns None when every node should be framed.
    """
    if node_ids is None:
        return None

    requested = [str(node_id) for node_id in node_ids]
    if not requested:
        raise ValueError("The node ids to frame are empty. Omit them to frame every node in the graph.")

    known = {str(node.id) for node in nodes}
    unknown = [node_id for node_id in requested if node_id not in known]
    if unknown:
        raise ValueError(f"Unknown node ids: {', '.join(unknown)}")
    return requested


def resolve_fit(
    fit: bool | None | Sequence[NodeIdType],
    nodes: Sequence[Node],
) -> tuple[bool | None, list[str] | None]:
    """Split the `fit` render option into whether to frame, and which nodes to frame.

    `bool` is checked before the id types, so `False`/`True` are the flag while a sequence is a set
    of node ids. A bare node id is rejected rather than accepted as a single-node list: an int flag
    (`0`/`1`) is indistinguishable from a node id, so guessing would silently frame a node.
    """
    if fit is None or isinstance(fit, bool):
        return fit, None

    if isinstance(fit, (str, bytes)) or not isinstance(fit, Sequence):
        raise TypeError(
            "`fit` must be a bool, None, or a sequence of node ids. Pass a list to frame specific "
            f"nodes, for example `fit=['0']`, not {fit!r}."
        )

    return True, resolve_fit_node_ids(fit, nodes)
