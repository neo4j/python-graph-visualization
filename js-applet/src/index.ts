import { FreeLayoutType, NVL } from '@neo4j-nvl/base'
import type { Node, NvlOptions, Relationship } from '@neo4j-nvl/base'
import { DragNodeInteraction, PanInteraction, ZoomInteraction, HoverInteraction } from '@neo4j-nvl/interaction-handlers'

interface PyNode extends Node {
  properties: Object;
}

interface PyRel extends Relationship {
  properties: Object;
}

class PyNVL {
  nvl: NVL

  zoomInteraction: ZoomInteraction

  panInteraction: PanInteraction

  dragNodeInteraction: DragNodeInteraction

  hoverInteraction: HoverInteraction

  constructor(
    frame: HTMLElement,
    tooltip: HTMLElement | null = null,
    nvlNodes: Node[] = [],
    nvlRels: Relationship[] = [],
    options: NvlOptions = {},
    callbacks = {}
  ) {

    this.nvl = new NVL(frame, nvlNodes, nvlRels, { ...options, disableTelemetry: true, disableWebWorkers: true, disableAria: true }, callbacks)
    this.zoomInteraction = new ZoomInteraction(this.nvl)
    this.panInteraction = new PanInteraction(this.nvl)
    this.dragNodeInteraction = new DragNodeInteraction(this.nvl)

    if (tooltip !== null) {
      this.hoverInteraction = new HoverInteraction(this.nvl)

      const truncateValue = (value: any, maxLength: number = 100): string => {
        const strValue = String(value);
        if (strValue.length <= maxLength) {
          return strValue;
        }
        return `<span class="tooltip-value">${strValue}</span>`;
      };

      this.hoverInteraction.updateCallback('onHover', (element: PyNode | PyRel) => {
        if (element === undefined) {
          tooltip.textContent = "";
          if (tooltip.style.display === "block") {
            tooltip.style.display = "none";
          }
        } else if ("from" in element) {
          const rel = element as PyRel

          let hoverInfo: string = (`<b>Source ID:</b> ${rel.from} </br><b>Target ID:</b> ${rel.to}`)
          for (const [key, value] of Object.entries(element.properties)) {
            hoverInfo += `</br><b>${key}:</b> ${truncateValue(value)}`
          }
          tooltip.setHTMLUnsafe(hoverInfo)

          if (tooltip.style.display === "none") {
            tooltip.style.display = "block";
          }
        } else if ("id" in element) {
          let hoverInfo: string = `<b>ID:</b> ${element.id}`
          for (const [key, value] of Object.entries(element.properties)) {
            hoverInfo += `</br><b>${key}:</b> ${truncateValue(value)}`
          }
          tooltip.setHTMLUnsafe(hoverInfo)

          if (tooltip.style.display === "none") {
            tooltip.style.display = "block";
          }
        }
      })
    }

    if (options.layout === FreeLayoutType) {
      this.nvl.setNodePositions(nvlNodes, false)
    }
  }
}

export { PyNVL as NVL }
