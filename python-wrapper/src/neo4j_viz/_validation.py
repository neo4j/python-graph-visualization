from __future__ import annotations

import warnings
from typing import Literal

from .node import Node
from .relationship import Relationship

OnDangling = Literal["error", "warn", "none"]

# Number of offending relationships to name in the message before truncating.
_MAX_REPORTED = 5


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
