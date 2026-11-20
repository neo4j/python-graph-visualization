"""The static PNG preview stored next to a widget's notebook output.

A committed notebook keeps only the outputs the kernel emitted, and a frontend that
cannot render widgets (GitHub, nbviewer) then shows nothing for a graph. The frontend
therefore snapshots the rendered canvas and sends it over the comm, and the kernel
stores it as an `image/png` output beside the widget.
"""

from __future__ import annotations

import uuid
import warnings

from IPython.display import display, update_display

# The snapshot arrives as a data URL; NVL produces PNGs base64-encoded.
PNG_META = "data:image/png;base64"

# Cap on a stored snapshot, in decoded bytes. Real snapshots sit far below this (tens to
# a few hundred KB); the cap only trims a very large canvas on a
# high-DPI display with a dense graph — where the base64 payload would bloat the notebook
# without adding a readable preview.
MAX_BYTES = 2 * 1024 * 1024


def split_data_url(data_url: str) -> tuple[str, str] | None:
    """Split a data URL into its metadata and payload, or `None` if it is not one.

    Shared with `GraphWidget.save`, which decodes the payload of the same URLs the
    frontend sends.
    """
    meta, separator, payload = data_url.partition(",")
    if not data_url.startswith("data:") or not separator:
        return None
    return meta, payload


class FallbackOutputs:
    """The static PNG snapshots stored next to one widget's outputs.

    A snapshot has to land in an output that already exists, so the widget displays an
    empty one ("slot") with a display id while its cell runs, and `store` fills it later
    with `update_display`. A widget can be displayed more than once — `_ipython_display_`
    runs again on every `display(widget)` — and each of those outputs holds its own copy
    of the image, so a snapshot refreshes all of them.

    A snapshot above `MAX_BYTES` is skipped, keeping the last one stored.
    """

    def __init__(self) -> None:
        self._slot_ids: list[str] = []
        self._warned = False

    def add_slot(self) -> None:
        """Display an empty output for a snapshot to be stored in later."""
        slot_id = f"neo4j-viz-image-{uuid.uuid4().hex}"
        self._slot_ids.append(slot_id)
        # IPython's display helpers are untyped, and mypy runs `no-untyped-call`.
        display({"text/plain": ""}, raw=True, display_id=slot_id)  # type: ignore[no-untyped-call]

    def store(self, data_url: str) -> None:
        """Store a snapshot from the frontend in every slot."""
        parts = split_data_url(data_url)
        if parts is None or parts[0] != PNG_META:
            return

        payload = parts[1]
        if len(payload) * 3 // 4 > MAX_BYTES:
            if not self._warned:
                self._warned = True
                warnings.warn(
                    f"Skipping the static PNG fallback: the snapshot is larger than "
                    f"{MAX_BYTES // (1024 * 1024)} MB, which would bloat the notebook. "
                    "Render a smaller graph or widget to store one, or set `fallback=False` to "
                    "silence this warning.",
                )
            return

        for slot_id in self._slot_ids:
            # IPython's display helpers are untyped, and mypy runs `no-untyped-call`.
            update_display(  # type: ignore[no-untyped-call]
                {"image/png": payload, "text/plain": "Graph visualization"},
                raw=True,
                display_id=slot_id,
            )
