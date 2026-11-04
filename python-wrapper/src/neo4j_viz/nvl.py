from __future__ import annotations

import json
import uuid
from importlib.resources import files

from IPython.display import HTML

from .node import Node
from .options import Legend, RenderOptions
from .relationship import Relationship
from .widget import _serialize_entity


# ── Template loading ─────────────────────────────────────────────────────
# The HTML template is built by Vite (vite build --config vite.config.html.ts)
# and ships as index.html in the package resources. It contains the full
# graph component with JS/CSS inlined. The standalone entrypoint reads graph
# data from an inert <script type="application/json" id="neo4j-viz-data">
# block; Python injects that block (with `<` escaped so no literal </script>
# can break out into executable markup) before the module script runs.
# The template hard-codes the container and data-block ids, so every render
# substitutes its own unique ids: otherwise several graphs sharing one page
# (notebook cells share a DOM document) would all resolve the first graph's
# container and data through getElementById.
class NVL:
    _CONTAINER_ID = "neo4j-viz-container"
    _DATA_ID = "neo4j-viz-data"

    def __init__(self) -> None:
        self._template = NVL._load_template()

    @classmethod
    def _load_template(cls) -> str:
        nvl_entry_point = files("neo4j_viz") / "resources" / "nvl_entrypoint"
        path = nvl_entry_point / "index.html"
        with path.open("r", encoding="utf-8") as f:
            return f.read()

    def render(
        self,
        nodes: list[Node],
        relationships: list[Relationship],
        render_options: RenderOptions,
        width: str,
        height: str,
        theme: str,
        legend: Legend | None = None,
    ) -> HTML:
        data_dict: dict[str, object] = {
            "nodes": [_serialize_entity(node) for node in nodes],
            "relationships": [_serialize_entity(rel) for rel in relationships],
            "width": width,
            "height": height,
            "theme": theme,
            "options": render_options.to_widget_options().to_json(),
            "legend": (legend or Legend()).to_json(),
        }
        # Escape `<` so no literal </script> can appear inside the block and
        # break out into executable markup (stored XSS). `<` is a valid JSON
        # escape, so JSON.parse restores the original text exactly. (`&` and
        # `>` are inert inside a script element's raw-text content, so they
        # need no escaping here.)
        data_json = json.dumps(data_dict).replace("<", "\\u003c")
        container_id = f"neo4j-viz-{uuid.uuid4().hex[:12]}"
        data_id = f"neo4j-viz-data-{uuid.uuid4().hex[:12]}"

        # Replace the fixed ids in the template — including the literals baked
        # into the JS bundle — before injecting the data, so user-supplied JSON
        # can never match and be rewritten. Unique ids let several graphs share
        # one page: notebook cells share a DOM document and getElementById
        # always resolves the first match.
        html = self._template
        html = html.replace(NVL._CONTAINER_ID, container_id)
        html = html.replace(NVL._DATA_ID, data_id)

        # Inject data as inert JSON — a browser never executes a
        # <script type="application/json"> block.
        data_script = f'<script type="application/json" id="{data_id}">{data_json}</script>'
        html = html.replace("</head>", f"{data_script}\n</head>", 1)

        return HTML(html)  # type: ignore[no-untyped-call]
