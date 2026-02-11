import "@neo4j-ndl/base/lib/neo4j-ds-styles.css";
import { GraphVisualization } from "@neo4j-ndl/react-graph";
import { createRoot } from "react-dom/client";

type ReactVisProps = {
  nodes: {
    id: string;
    caption?: string;
    size?: number;
    color?: string;
    pinned?: boolean;
    properties: Record<string, any>;
  }[];
  relationships: {
    id: string;
    from: string;
    to: string;
    caption?: string;
    color?: string;
    width?: number;
    properties: Record<string, any>;
  }[];
};

export function mountReactComponent(
  elementId: string,
  { nodes, relationships }: ReactVisProps,
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
            labels:
              node.properties.labels ?? (node.caption ? [node.caption] : []),
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
              {} as Record<string, any>,
            ),
          }))}
          rels={relationships.map((rel) => ({
            id: rel.id,
            type: rel.properties.type ?? rel.caption ?? "",
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
              {} as Record<string, any>,
            ),
            from: rel.from,
            to: rel.to,
          }))}
        />
      </div>,
    );
    return root;
  }
  return null;
}
