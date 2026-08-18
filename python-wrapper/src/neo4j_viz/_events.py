"""Internal helpers for the widget's interaction-event API.

The public surface is the ``GraphWidget.on_node_event`` / ``on_relationship_event`` /
``on_canvas_event`` methods, which accept a short `~neo4j_viz.options.MouseEvent` string
(``"click"`` / ``"double_click"`` / ``"right_click"``). These helpers validate that string at
runtime (via a private enum) and map it to the full ``last_event.type`` wire format
(``"<category>_<mouse_event>"``, e.g. ``"node_double_click"``) that the frontend emits and that
``InteractionEvent.type`` carries.
"""

from __future__ import annotations

from enum import Enum

from .options import InteractionEventType, MouseEvent


class _MouseEvent(str, Enum):
    """The mouse-event half of an interaction.

    Used to validate the short gesture strings accepted by the ``on_*_event`` methods (raising a
    clear ``ValueError`` on an unknown value, so typos are caught at registration time even without
    a type checker) and to map them to the full ``last_event.type`` wire format.
    """

    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"


def _to_full_event_type(category: str, mouse_event: MouseEvent) -> InteractionEventType:
    """Validate ``mouse_event`` and join it with ``category`` into a full ``last_event.type``.

    ``category`` is one of ``"node"`` / ``"relationship"`` / ``"canvas"`` (implied by which
    ``on_*_event`` method was called). The result matches the frontend's ``InteractionEvent.type``
    wire format verbatim.
    """
    return f"{category}_{_MouseEvent(mouse_event).value}"  # type: ignore[return-value]
