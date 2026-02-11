import "@neo4j-ndl/base/lib/neo4j-ds-styles.css";
import { GraphVisualization } from "@neo4j-ndl/react-graph";
import type { Layout, NvlOptions } from "@neo4j-nvl/base";
import { createRoot, type Root } from "react-dom/client";

type NodeData = {
  id: string;
  caption?: string;
  size?: number;
  color?: string;
  pinned?: boolean;
  properties: Record<string, any>;
};

type RelationshipData = {
  id: string;
  from: string;
  to: string;
  caption?: string;
  color?: string;
  width?: number;
  properties: Record<string, any>;
};

type GraphOptions = {
  layout?: Layout;
  nvlOptions?: Partial<NvlOptions>;
  zoom?: number;
  pan?: { x: number; y: number };
  layoutOptions?: Record<string, any>;
};

function transformNodes(nodes: NodeData[]) {
  return nodes.map((node) => ({
    id: node.id,
    // Only include visual properties when explicitly set, so that
    // GraphVisualization's smart defaults (label-based coloring, etc.) apply.
    ...(node.color !== undefined && { color: node.color }),
    ...(node.size !== undefined && { size: node.size }),
    ...(node.pinned !== undefined && { pinned: node.pinned }),
    labels: node.properties.labels ?? (node.caption ? [node.caption] : []),
    properties: Object.entries(node.properties).reduce(
      (acc, [key, value]) => {
        if (key === "labels") return acc;
        const type = typeof value;
        acc[key] = {
          stringified: type === "string" ? `"${value}"` : String(value),
          type,
        };
        return acc;
      },
      {} as Record<string, any>,
    ),
  }));
}

function transformRelationships(relationships: RelationshipData[]) {
  return relationships.map((rel) => ({
    id: rel.id,
    ...(rel.color !== undefined && { color: rel.color }),
    ...(rel.width !== undefined && { width: rel.width }),
    type: rel.properties.type ?? rel.caption ?? "",
    properties: Object.entries(rel.properties).reduce(
      (acc, [key, value]) => {
        if (key === "type") return acc;
        acc[key] = {
          stringified: String(value),
          type: typeof value,
        };
        return acc;
      },
      {} as Record<string, any>,
    ),
    from: rel.from,
    to: rel.to,
  }));
}

function renderGraph(
  el: HTMLElement,
  nodes: NodeData[],
  relationships: RelationshipData[],
  options: GraphOptions = {},
): Root {
  const { layout, nvlOptions, zoom, pan, layoutOptions } = options;
  const root = createRoot(el);
  root.render(
    <div style={{ height: "100%", width: "100%" }}>
      <GraphVisualization
        nodes={transformNodes(nodes)}
        rels={transformRelationships(relationships)}
        layout={layout}
        nvlOptions={nvlOptions}
        zoom={zoom}
        pan={pan}
        layoutOptions={layoutOptions}
      />
    </div>,
  );
  return root;
}

// ── anywidget entry point ──────────────────────────────────────────────
// Called by anywidget (Jupyter) and by the standalone HTML model shim.
// `model` has traitlet-synced data (or a static shim), `el` is the DOM container.
function render({ model, el }: { model: any; el: HTMLElement }) {
  el.style.height = model.get("height") ?? "600px";
  el.style.width = model.get("width") ?? "100%";

  const nodes: NodeData[] = model.get("nodes") ?? [];
  const relationships: RelationshipData[] = model.get("relationships") ?? [];
  const options: GraphOptions = model.get("options") ?? {};

  const root = renderGraph(el, nodes, relationships, options);

  // Re-render when Python-side data changes (no-op for static HTML shim)
  function onDataChange() {
    const updatedNodes: NodeData[] = model.get("nodes") ?? [];
    const updatedRels: RelationshipData[] = model.get("relationships") ?? [];
    const updatedOptions: GraphOptions = model.get("options") ?? {};
    const { layout, nvlOptions, zoom, pan, layoutOptions } = updatedOptions;
    root.render(
      <div style={{ height: "100%", width: "100%" }}>
        <GraphVisualization
          nodes={transformNodes(updatedNodes)}
          rels={transformRelationships(updatedRels)}
          layout={layout}
          nvlOptions={nvlOptions}
          zoom={zoom}
          pan={pan}
          layoutOptions={layoutOptions}
        />
      </div>,
    );
  }

  model.on("change:nodes", onDataChange);
  model.on("change:relationships", onDataChange);
  model.on("change:options", onDataChange);
  model.on("change:height", () => {
    el.style.height = model.get("height") ?? "600px";
  });
  model.on("change:width", () => {
    el.style.width = model.get("width") ?? "100%";
  });

  return () => {
    root.unmount();
  };
}

export default { render };
