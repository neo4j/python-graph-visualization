import "@neo4j-ndl/base/lib/neo4j-ds-styles.css";
import type { NeoNode, NeoRel, PortableProperty } from "@neo4j-ndl/react-graph";
import { GraphVisualization } from "@neo4j-ndl/react-graph";
import type { Layout, NvlOptions } from "@neo4j-nvl/base";
import { Component, type ErrorInfo, type ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";

// ── Types ──────────────────────────────────────────────────────────────

/** Node as serialized from the Python side (raw properties, no labels array). */
type SerializedNode = {
  id: string;
  caption?: string;
  size?: number;
  color?: string;
  pinned?: boolean;
  properties: Record<string, unknown>;
};

/** Relationship as serialized from the Python side (raw properties, no type field). */
type SerializedRelationship = {
  id: string;
  from: string;
  to: string;
  caption?: string;
  color?: string;
  width?: number;
  properties: Record<string, unknown>;
};

type GraphOptions = {
  layout?: Layout;
  nvlOptions?: Partial<NvlOptions>;
  zoom?: number;
  pan?: { x: number; y: number };
  layoutOptions?: Record<string, unknown>;
};

/**
 * Anywidget model interface — the contract for `model` in the `render()` entry point.
 * In the anywidget path, this is a real traitlet-backed model.
 * In the HTML fallback, this is a lightweight shim (get/set/on/save_changes).
 */
interface AnywidgetModel {
  get(key: "nodes"): SerializedNode[] | undefined;
  get(key: "relationships"): SerializedRelationship[] | undefined;
  get(key: "options"): GraphOptions | undefined;
  get(key: "height"): string | undefined;
  get(key: "width"): string | undefined;
  on(event: string, callback: () => void): void;
}

// ── Error Boundary ─────────────────────────────────────────────────────

type ErrorBoundaryProps = { children: ReactNode };
type ErrorBoundaryState = { error: Error | null };

class GraphErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[neo4j-viz] Rendering error:", error, info.componentStack);
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div
          style={{
            padding: "24px",
            fontFamily: "system-ui, sans-serif",
            color: "#c0392b",
            background: "#fdf0ef",
            borderRadius: "8px",
            border: "1px solid #e6b0aa",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
          }}
        >
          <h3 style={{ margin: "0 0 8px" }}>Graph rendering failed</h3>
          <pre
            style={{
              margin: 0,
              whiteSpace: "pre-wrap",
              fontSize: "13px",
              color: "#6c3428",
            }}
          >
            {this.state.error.message}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

// ── Transform helpers ──────────────────────────────────────────────────

function transformNodes(nodes: SerializedNode[]): NeoNode[] {
  return nodes.map((node) => {
    const labels = node.properties.labels;
    return {
      id: node.id,
      // Only include visual properties when explicitly set, so that
      // GraphVisualization's smart defaults (label-based coloring, etc.) apply.
      ...(node.color !== undefined && { color: node.color }),
      ...(node.size !== undefined && { size: node.size }),
      ...(node.pinned !== undefined && { pinned: node.pinned }),
      labels: Array.isArray(labels)
        ? (labels as string[])
        : node.caption
          ? [node.caption]
          : [],
      properties: Object.entries(node.properties).reduce<
        Record<string, PortableProperty>
      >((acc, [key, value]) => {
        if (key === "labels") return acc;
        const type = typeof value;
        acc[key] = {
          stringified: type === "string" ? `"${value}"` : String(value),
          type,
        };
        return acc;
      }, {}),
    };
  });
}

function transformRelationships(
  relationships: SerializedRelationship[],
): NeoRel[] {
  return relationships.map((rel) => ({
    id: rel.id,
    ...(rel.color !== undefined && { color: rel.color }),
    ...(rel.width !== undefined && { width: rel.width }),
    type: (rel.properties.type as string | undefined) ?? rel.caption ?? "",
    properties: Object.entries(rel.properties).reduce<
      Record<string, PortableProperty>
    >((acc, [key, value]) => {
      if (key === "type") return acc;
      acc[key] = {
        stringified: String(value),
        type: typeof value,
      };
      return acc;
    }, {}),
    from: rel.from,
    to: rel.to,
  }));
}

// ── Rendering ──────────────────────────────────────────────────────────

function renderGraph(
  el: HTMLElement,
  nodes: SerializedNode[],
  relationships: SerializedRelationship[],
  options: GraphOptions = {},
): Root {
  const { layout, nvlOptions, zoom, pan, layoutOptions } = options;
  const root = createRoot(el);
  root.render(
    <GraphErrorBoundary>
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
      </div>
    </GraphErrorBoundary>,
  );
  return root;
}

// ── anywidget entry point ──────────────────────────────────────────────
// Called by anywidget (Jupyter) and by the standalone HTML model shim.
// `model` has traitlet-synced data (or a static shim), `el` is the DOM container.
function render({ model, el }: { model: AnywidgetModel; el: HTMLElement }) {
  el.style.height = model.get("height") ?? "600px";
  el.style.width = model.get("width") ?? "100%";

  const nodes = model.get("nodes") ?? [];
  const relationships = model.get("relationships") ?? [];
  const options = model.get("options") ?? {};

  const root = renderGraph(el, nodes, relationships, options);

  // Re-render when Python-side data changes (no-op for static HTML shim)
  function onDataChange() {
    const updatedNodes = model.get("nodes") ?? [];
    const updatedRels = model.get("relationships") ?? [];
    const updatedOptions = model.get("options") ?? {};
    const { layout, nvlOptions, zoom, pan, layoutOptions } = updatedOptions;
    root.render(
      <GraphErrorBoundary>
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
        </div>
      </GraphErrorBoundary>,
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
