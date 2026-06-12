from __future__ import annotations

import json
import uuid
from importlib.resources import files

from IPython.display import HTML

from .node import Node
from .options import RenderOptions
from .relationship import Relationship
from .widget import _serialize_entity


# ── Template loading ─────────────────────────────────────────────────────
# The HTML template is built by Vite (vite build --config vite.config.html.ts)
# and ships as index.html in the package resources. It contains the full
# graph component with JS/CSS inlined, and reads graph data from
# window.__NEO4J_VIZ_DATA__.  Python just injects a <script> setting that
# variable before the module script runs.
class NVL:
    _CONTAINER_ID = "neo4j-viz-container"

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
    ) -> HTML:
        data_dict: dict[str, object] = {
            "nodes": [_serialize_entity(node) for node in nodes],
            "relationships": [_serialize_entity(rel) for rel in relationships],
            "width": width,
            "height": height,
            "theme": theme,
            "options": render_options.to_widget_options().to_json(),
        }
        data_json = json.dumps(data_dict)
        container_id = f"neo4j-viz-{uuid.uuid4().hex[:12]}"

        # Inject data and unique container ID into the built template.
        data_script = f"<script>window.__NEO4J_VIZ_DATA__ = {data_json};</script>"
        html = self._template
        html = html.replace("</head>", f"{data_script}\n</head>", 1)
        html = html.replace(NVL._CONTAINER_ID, container_id)

        return HTML(html)  # type: ignore[no-untyped-call]
