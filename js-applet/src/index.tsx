import "@neo4j-ndl/base/lib/neo4j-ds-styles.css";
import { GraphVisualization } from "@neo4j-ndl/react-graph";
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

function transformNodes(nodes: NodeData[]) {
  return nodes.map((node) => ({
    id: node.id,
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
): Root {
  const root = createRoot(el);
  root.render(
    <div style={{ height: "100%", width: "100%" }}>
      <GraphVisualization
        nodes={transformNodes(nodes)}
        rels={transformRelationships(relationships)}
      />
    </div>,
  );
  return root;
}

// ── anywidget entry point ──────────────────────────────────────────────
// Called by anywidget. `model` has traitlet-synced data, `el` is the DOM container.
export function render({ model, el }: { model: any; el: HTMLElement }) {
  el.style.height = model.get("height") ?? "600px";
  el.style.width = model.get("width") ?? "100%";

  const nodes: NodeData[] = model.get("nodes") ?? [];
  const relationships: RelationshipData[] = model.get("relationships") ?? [];

  const root = renderGraph(el, nodes, relationships);

  // Re-render when Python-side data changes
  function onDataChange() {
    const updatedNodes: NodeData[] = model.get("nodes") ?? [];
    const updatedRels: RelationshipData[] = model.get("relationships") ?? [];
    root.render(
      <div style={{ height: "100%", width: "100%" }}>
        <GraphVisualization
          nodes={transformNodes(updatedNodes)}
          rels={transformRelationships(updatedRels)}
        />
      </div>,
    );
  }

  model.on("change:nodes", onDataChange);
  model.on("change:relationships", onDataChange);
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

// ── HTML fallback entry point ──────────────────────────────────────────
// Called from inline <script> when anywidget is not available (Streamlit, static HTML).
export function mountReactComponent(
  elementId: string,
  {
    nodes,
    relationships,
  }: { nodes: NodeData[]; relationships: RelationshipData[] },
): Root | null {
  const container = document.getElementById(elementId);
  if (!container) return null;
  return renderGraph(container, nodes, relationships);
}
