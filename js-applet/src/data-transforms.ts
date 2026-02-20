import "@neo4j-ndl/base/lib/neo4j-ds-styles.css";
import type { NeoNode, NeoRel, PortableProperty } from "@neo4j-ndl/react-graph";

export type SerializedNode = {
  id: string;
  caption?: string;
  size?: number;
  color?: string;
  pinned?: boolean;
  properties: Record<string, unknown>;
};

function isListOfStrings(value: unknown): value is string[] {
  return (
    Array.isArray(value) && value.every((item) => typeof item === "string")
  );
}

export type SerializedRelationship = {
  id: string;
  from: string;
  to: string;
  caption?: string;
  color?: string;
  width?: number;
  properties: Record<string, unknown>;
};

export function transformNodes(nodes: SerializedNode[]): NeoNode[] {
  return nodes.map((node) => {
    const labelProperty = isListOfStrings(node.properties.labels)
      ? node.properties.labels
      : [];
    return {
      id: node.id,
      // Only include visual properties when explicitly set, so that
      // GraphVisualization's smart defaults (label-based coloring, etc.) apply.
      ...(node.color !== undefined && { color: node.color }),
      ...(node.size !== undefined && { size: node.size }),
      ...(node.pinned !== undefined && { pinned: node.pinned }),
      labels: node.caption
          ? [node.caption]
          : labelProperty,
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

export function transformRelationships(
  relationships: SerializedRelationship[],
): NeoRel[] {
  return relationships.map((rel) => ({
    id: rel.id,
    ...(rel.color !== undefined && { color: rel.color }),
    ...(rel.width !== undefined && { width: rel.width }),
    type: rel.caption ?? (rel.properties.type as string | undefined) ?? "",
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
