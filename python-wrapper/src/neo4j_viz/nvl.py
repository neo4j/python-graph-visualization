from __future__ import annotations

import json
import uuid
from importlib.resources import files

from IPython.display import HTML

from .node import Node
from .relationship import Relationship
from .widget import _serialize_entity


class NVL:
    """HTML fallback renderer for standalone HTML / Streamlit.

    Loads the same ESM widget bundle used by anywidget, but runs it
    through a lightweight model shim instead of the Jupyter widget
    protocol.  This means both rendering paths execute identical JS.
    """

    def __init__(self) -> None:
        nvl_entry_point = files("neo4j_viz") / "resources" / "nvl_entrypoint"

        js_path = nvl_entry_point / "widget.js"
        with js_path.open("r", encoding="utf-8") as file:
            self.widget_js = file.read()

        css_path = nvl_entry_point / "style.css"
        with css_path.open("r", encoding="utf-8") as file:
            self.widget_css = file.read()

    def render(
        self,
        nodes: list[Node],
        relationships: list[Relationship],
        width: str,
        height: str,
    ) -> HTML:
        nodes_json = json.dumps([_serialize_entity(node) for node in nodes])
        rels_json = json.dumps([_serialize_entity(rel) for rel in relationships])
        width_json = json.dumps(width)
        height_json = json.dumps(height)

        container_id = str(uuid.uuid4())

        # The widget.js ESM bundle is loaded via a Blob URL so we can
        # dynamically import() it and call the exported render() function
        # with a static model shim.
        widget_js_json = json.dumps(self.widget_js)

        html_output = f"""
        <style>
            {self.widget_css}
        </style>
        <div id="{container_id}" style="width: {width}; height: {height};"></div>

        <script type="module">
            // Detect light/dark theme from page background
            const bg = window.getComputedStyle(document.body).getPropertyValue('background-color');
            const rgb = bg.match(/\\d+/g);
            if (rgb) {{
                const brightness = Number(rgb[0]) * 0.2126 + Number(rgb[1]) * 0.7152 + Number(rgb[2]) * 0.0722;
                document.documentElement.className = brightness < 128 ? "dark" : "light";
            }}

            // Load the ESM widget bundle via Blob URL
            const code = {widget_js_json};
            const blob = new Blob([code], {{ type: 'application/javascript' }});
            const url = URL.createObjectURL(blob);
            const {{ render }} = await import(url);
            URL.revokeObjectURL(url);

            // Static model shim — same interface as anywidget's model,
            // but read-only (no two-way sync needed for standalone HTML).
            const data = {{
                nodes: {nodes_json},
                relationships: {rels_json},
                width: {width_json},
                height: {height_json}
            }};
            const model = {{
                get(key) {{ return data[key]; }},
                on() {{}},
                set() {{}},
                save_changes() {{}}
            }};

            const el = document.getElementById('{container_id}');
            render({{ model, el }});
        </script>
        """

        return HTML(html_output)  # type: ignore[no-untyped-call]
