from __future__ import annotations

import json
import uuid
from importlib.resources import files
from typing import Union

from IPython.display import HTML

from .node import Node
from .options import RenderOptions
from .relationship import Relationship


class NVL:
    def __init__(self) -> None:
        # at which point we get None?
        base_folder = files("neo4j_viz")
        resource_folder = base_folder / "resources"
        nvl_entry_point = resource_folder / "nvl_entrypoint"

        js_path = nvl_entry_point / "base.js"
        with js_path.open("r", encoding="utf-8") as file:
            self.library_code = file.read()

        styles_path = nvl_entry_point / "styles.css"
        with styles_path.open("r", encoding="utf-8") as file:
            self.styles = file.read()

        icons = resource_folder / "icons"

        zoom_in_path = icons / "zoom-in.svg"
        with zoom_in_path.open("r", encoding="utf-8") as file:
            self.zoom_in_svg = file.read()

        zoom_out_path = icons / "zoom-out.svg"
        with zoom_out_path.open("r", encoding="utf-8") as file:
            self.zoom_out_svg = file.read()

        screenshot_path = icons / "screenshot.svg"
        with screenshot_path.open("r", encoding="utf-8") as file:
            self.screenshot_svg = file.read()

    @staticmethod
    def _serialize_entity(entity: Union[Node, Relationship]) -> str:
        try:
            entity_dict = entity.to_dict()
            return json.dumps(entity_dict)
        except TypeError:
            props_as_strings = {}
            for k, v in entity_dict["properties"].items():
                try:
                    json.dumps(v)
                except TypeError:
                    props_as_strings[k] = str(v)
            entity_dict["properties"].update(props_as_strings)

            try:
                return json.dumps(entity_dict)
            except TypeError as e:
                # This should never happen anymore, but just in case
                if "not JSON serializable" in str(e):
                    raise ValueError(f"A field of a {type(entity).__name__} object is not supported: {str(e)}")
                else:
                    raise e

    def render(
        self,
        nodes: list[Node],
        relationships: list[Relationship],
        render_options: RenderOptions,
        width: str,
        height: str,
        show_hover_tooltip: bool,
    ) -> HTML:
        nodes_json = f"[{','.join([self._serialize_entity(node) for node in nodes])}]"
        rels_json = f"[{','.join([self._serialize_entity(rel) for rel in relationships])}]"

        render_options_json = json.dumps(render_options.to_dict())
        container_id = str(uuid.uuid4())
        react_container_id = container_id + "-react"

        if show_hover_tooltip:
            hover_element = f"document.getElementById('{container_id}-tooltip')"
            hover_div = f'<div id="{container_id}-tooltip" class="tooltip" style="display: none;"></div>'
        else:
            hover_element = "null"
            hover_div = ""

        # Using a different varname for every instance, so that a notebook
        # can use several instances without unwanted interactions.
        # The first part of the UUID should be "unique enough" in this context.
        nvl_varname = "graph_" + container_id.split("-")[0]
        download_name = nvl_varname + ".png"

        js_code = f"""
        var {nvl_varname} = new NVLBase.NVL(
            document.getElementById('{container_id}'),
            {hover_element},
            {nodes_json},
            {rels_json},
            {render_options_json},
        );

        // Mount React component using the exported function
        if (typeof mountReactComponent === 'function') {{
            mountReactComponent('{react_container_id}', {{ 
                message: 'React component rendered with {len(nodes)} nodes and {len(relationships)} relationships!' 
            }});
        }}
        """
        full_code = self.library_code + js_code

        html_output = f"""
        <style>
            {self.styles}
        </style>
        <div style="display: flex; flex-direction: column; gap: 10px;">
            <div id="{react_container_id}" style="width: {width};"></div>
            <div id="{container_id}" style="width: {width}; height: {height}; position: relative;">
                <div style="position: absolute; z-index: 2147483647; right: 0; top: 0; padding: 1rem">
                    <button type="button" title="Save as PNG" onclick="{nvl_varname}.nvl.saveToFile({{ filename: '{download_name}' }})" class="icon">
                        {self.screenshot_svg}
                    </button>
                    <button type="button" title="Zoom in" onclick="{nvl_varname}.nvl.setZoom({nvl_varname}.nvl.getScale() + 0.5)" class="icon">
                        {self.zoom_in_svg}
                    </button>
                    <button type="button" title="Zoom out" onclick="{nvl_varname}.nvl.setZoom({nvl_varname}.nvl.getScale() - 0.5)" class="icon">
                        {self.zoom_out_svg}
                    </button>
                </div>
                {hover_div}
            </div>
        </div>

        <script>
            getTheme = () => {{
                const backgroundColorString = window.getComputedStyle(document.body, null).getPropertyValue('background-color')
                const colorsArray = backgroundColorString.match(/\\d+/g);
                const brightness = Number(colorsArray[0]) * 0.2126 + Number(colorsArray[1]) * 0.7152 + Number(colorsArray[2]) * 0.0722
                return brightness < 128 ? "dark" : "light"
            }}
            document.documentElement.className = getTheme()

            {full_code}
        </script>
        """

        return HTML(html_output)  # type: ignore[no-untyped-call]
