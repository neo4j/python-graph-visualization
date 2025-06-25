import "@neo4j-ndl/base/lib/neo4j-ds-styles.css";
import type { Node, NvlOptions, Relationship } from "@neo4j-nvl/base";
import { FreeLayoutType, NVL } from "@neo4j-nvl/base";
import {
  DragNodeInteraction,
  HoverInteraction,
  PanInteraction,
  ZoomInteraction,
} from "@neo4j-nvl/interaction-handlers";
import React from "react";
import ReactDOM from "react-dom/client";
import { TestComponent } from "./TestComponent";

interface PyNode extends Node {
  properties: Object;
}

interface PyRel extends Relationship {
  properties: Object;
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

// Export a function to mount React components
export function mountReactComponent(elementId: string, props: any = {}) {
  const container = document.getElementById(elementId);
  if (container && typeof ReactDOM !== "undefined") {
    const root = ReactDOM.createRoot(container);
    root.render(React.createElement(TestComponent, props));
    return root;
  }
  return null;
}

// Make it available globally
(window as any).mountReactComponent = mountReactComponent;
