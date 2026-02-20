import "@neo4j-ndl/base/lib/neo4j-ds-styles.css";
import type { NeoNode, NeoRel, PortableProperty } from "@neo4j-ndl/react-graph";
import type { Node, Relationship } from "@neo4j-nvl/base";

export type SerializedNode = { properties: Record<string, unknown> } & Node;

function isListOfStrings(value: unknown): value is string[] {
  return (
    Array.isArray(value) && value.every((item) => typeof item === "string")
  );
}

export function transformNodes(nodes: SerializedNode[]): NeoNode[] {
  return nodes.map((node) => {
    const labelProperty = isListOfStrings(node.properties.labels)
      ? node.properties.labels
      : [];
    return {
      ...node,
      id: node.id,
      // This is done so that the overview panel breaks down by caption, rather than labels
      labels: node.caption ? [node.caption] : labelProperty,
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

export type SerializedRelationship = { properties: Record<string, unknown> } & Relationship;

export function transformRelationships(
  relationships: SerializedRelationship[],
): NeoRel[] {
  return relationships.map((rel) => ({
    ...rel,
    id: rel.id,
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
