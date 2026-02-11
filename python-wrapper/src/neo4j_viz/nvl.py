from __future__ import annotations

import json
import uuid
from importlib.resources import files

from IPython.display import HTML

from .node import Node
from .relationship import Relationship
from .widget import _DEV, _DEV_SERVER, _serialize_entity

# ── Template loading ─────────────────────────────────────────────────────
# The HTML template is built by Vite (vite build --config vite.config.html.ts)
# and ships as index.html in the package resources. It contains the full
# graph component with JS/CSS inlined, and reads graph data from
# window.__NEO4J_VIZ_DATA__.  Python just injects a <script> setting that
# variable before the module script runs.

_CONTAINER_ID = "neo4j-viz-container"


def _load_template() -> str:
    nvl_entry_point = files("neo4j_viz") / "resources" / "nvl_entrypoint"
    path = nvl_entry_point / "index.html"
    with path.open("r", encoding="utf-8") as f:
        return f.read()


# Dev mode: minimal HTML that imports from the Vite dev server.
# Structurally identical to what the built template does, but loads
# JS live from Vite for hot reloading.
_DEV_TEMPLATE = """\
<div id="{container_id}" style="width: {width}; height: {height};"></div>
<script>window.__NEO4J_VIZ_DATA__ = {data_json};</script>
<script type="module">
    import widget from "{dev_server}/src/index.tsx";

    const bg = window.getComputedStyle(document.body).getPropertyValue('background-color');
    const rgb = bg.match(/\\d+/g);
    if (rgb) {{
        const brightness = Number(rgb[0]) * 0.2126 + Number(rgb[1]) * 0.7152 + Number(rgb[2]) * 0.0722;
        document.documentElement.className = brightness < 128 ? "dark" : "light";
    }}

    const data = window.__NEO4J_VIZ_DATA__;
    const model = {{
        get(key) {{ return data[key]; }},
        on() {{}},
        set() {{}},
        save_changes() {{}}
    }};

    const el = document.getElementById('{container_id}');
    el.style.width = data.width ?? "100%";
    el.style.height = data.height ?? "600px";
    widget.render({{ model, el }});
</script>"""


class NVL:
    """HTML fallback renderer for standalone HTML / Streamlit.

    Uses the same Vite-built HTML template as the dev harness (index.html).
    Python injects graph data via window.__NEO4J_VIZ_DATA__ — no blob URLs,
    no manual JS/CSS inlining.

    In dev mode (NEO4J_VIZ_DEV=1), imports JS from the Vite dev server
    for hot reloading with real Python data.
    """

    def __init__(self) -> None:
        if not _DEV:
            self._template = _load_template()

    def render(
        self,
        nodes: list[Node],
        relationships: list[Relationship],
        width: str,
        height: str,
        options: dict[str, object] | None = None,
    ) -> HTML:
        data_dict: dict[str, object] = {
            "nodes": [_serialize_entity(node) for node in nodes],
            "relationships": [_serialize_entity(rel) for rel in relationships],
            "width": width,
            "height": height,
            "options": options or {},
        }
        data_json = json.dumps(data_dict)
        container_id = f"neo4j-viz-{uuid.uuid4().hex[:12]}"

        if _DEV:
            html = _DEV_TEMPLATE.format(
                container_id=container_id,
                width=width,
                height=height,
                data_json=data_json,
                dev_server=_DEV_SERVER,
            )
        else:
            # Inject data and unique container ID into the built template.
            data_script = f'<script>window.__NEO4J_VIZ_DATA__ = {data_json};</script>'
            html = self._template
            html = html.replace("</head>", f"{data_script}\n</head>", 1)
            html = html.replace(_CONTAINER_ID, container_id)

        return HTML(html)  # type: ignore[no-untyped-call]
