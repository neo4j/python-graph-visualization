import "@neo4j-ndl/base/lib/neo4j-ds-styles.css";
import { GraphVisualization } from "@neo4j-ndl/react";
import type { Node, NvlOptions, Relationship } from "@neo4j-nvl/base";
import { FreeLayoutType, NVL } from "@neo4j-nvl/base";
import {
  DragNodeInteraction,
  HoverInteraction,
  PanInteraction,
  ZoomInteraction,
} from "@neo4j-nvl/interaction-handlers";
import { createRoot } from "react-dom/client";

interface PyNode extends Node {
  properties: Record<string, any>;
}

interface PyRel extends Relationship {
  properties: Record<string, any>;
  from: string;
  to: string;
}

class PyNVL {
  nvl: NVL;

  zoomInteraction: ZoomInteraction;

  panInteraction: PanInteraction;

  dragNodeInteraction: DragNodeInteraction;

  hoverInteraction: HoverInteraction;

  constructor(
    frame: HTMLElement,
    tooltip: HTMLElement | null = null,
    nvlNodes: Node[] = [],
    nvlRels: Relationship[] = [],
    options: NvlOptions = {},
    callbacks = {}
  ) {
    this.nvl = new NVL(
      frame,
      nvlNodes,
      nvlRels,
      {
        ...options,
        disableTelemetry: true,
        disableWebWorkers: true,
        disableAria: true,
      },
      callbacks
    );
    this.zoomInteraction = new ZoomInteraction(this.nvl);
    this.panInteraction = new PanInteraction(this.nvl);
    this.dragNodeInteraction = new DragNodeInteraction(this.nvl);

    if (tooltip !== null) {
      this.hoverInteraction = new HoverInteraction(this.nvl);

      this.hoverInteraction.updateCallback(
        "onHover",
        (element: PyNode | PyRel) => {
          if (element === undefined) {
            tooltip.textContent = "";
            if (tooltip.style.display === "block") {
              tooltip.style.display = "none";
            }
          } else if ("from" in element) {
            const rel = element as PyRel;

            let hoverInfo: string = `<b>sauce ID:</b> ${rel.from} </br><b>Target ID:</b> ${rel.to}`;
            for (const [key, value] of Object.entries(element.properties)) {
              hoverInfo += `</br><b>${key}:</b> ${value}`;
            }
            tooltip.setHTMLUnsafe(hoverInfo);

            if (tooltip.style.display === "none") {
              tooltip.style.display = "block";
            }
          } else if ("id" in element) {
            let hoverInfo: string = `<b>ID:</b> ${element.id}`;
            for (const [key, value] of Object.entries(element.properties)) {
              hoverInfo += `</br><b>${key}:</b> ${value}`;
            }
            tooltip.setHTMLUnsafe(hoverInfo);

            if (tooltip.style.display === "none") {
              tooltip.style.display = "block";
            }
          }
        }
      );
    }

    if (options.layout === FreeLayoutType) {
      this.nvl.setNodePositions(nvlNodes, false);
    }
  }
}

export { PyNVL as NVL };

type ReactVisProps = {
  nodes: PyNode[];
  relationships: PyRel[];
};

export function mountReactComponent(
  elementId: string,
  { nodes, relationships }: ReactVisProps
) {
  console.log("mountReactComponent", nodes, relationships);
  const container = document.getElementById(elementId);
  if (container) {
    console.log("mounting");
    const root = createRoot(container);
    root.render(
      <div style={{ height: "500px", width: "100%" }}>
        <GraphVisualization
          nodes={nodes.map((node) => ({
            id: node.id,
            labels: node.properties.labels,
            properties: Object.entries(node.properties).reduce(
              (acc, [key, value]) => {
                if (key === "labels") {
                  return acc;
                }
                const type = typeof value;
                acc[key] = {
                  stringified:
                    type === "string" ? `"${value}"` : value.toString(),
                  type,
                };
                return acc;
              },
              {} as Record<string, any>
            ),
          }))}
          rels={relationships.map((rel) => ({
            id: rel.id,
            type: rel.properties.type,
            properties: Object.entries(rel.properties).reduce(
              (acc, [key, value]) => {
                if (key === "type") {
                  return acc;
                }
                acc[key] = {
                  stringified: value.toString(),
                  type: typeof value,
                };
                return acc;
              },
              {} as Record<string, any>
            ),
            from: rel.from,
            to: rel.to,
          }))}
        />
      </div>
    );
    return root;
  }
  return null;
}
