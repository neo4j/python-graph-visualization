import type { LayoutOptions } from "@neo4j-nvl/base";
import type { SerializedNode } from "./data-transforms";

// NVL's `clusterBy` is a function, which can't be serialized from Python. Python instead sends
// the name of a node property; we resolve it against the serialized nodes into the function
// NVL expects. Nodes missing the property are left independent (undefined).
type ClusterByFn = (nodeId: string) => string | undefined;

function buildClusterBy(property: string, nodes: SerializedNode[]): ClusterByFn {
  const clusterByNodeId = new Map<string, unknown>();
  for (const node of nodes) {
    clusterByNodeId.set(String(node.id), node.properties[property]);
  }

  return (nodeId) => {
    const value = clusterByNodeId.get(nodeId);
    return value == null ? undefined : String(value);
  };
}

function resolveClusterBy(value: unknown, nodes: SerializedNode[]): ClusterByFn | undefined {
  return typeof value === "string" ? buildClusterBy(value, nodes) : undefined;
}

/**
 * Turn the declarative clustering spec sent from Python into the function NVL expects.
 *
 * Python sends `clusterBy` as a node property name (a string). This handles both the
 * force-directed layout (`layoutOptions.clustering.clusterBy`) and the hierarchical layout
 * (`layoutOptions.clusterBy`). Everything else is passed through unchanged, and the original
 * object is returned when there is nothing to resolve (so callers keep a stable reference).
 */
export function buildLayoutOptions(
  layoutOptions: Record<string, unknown> | undefined,
  nodes: SerializedNode[],
): LayoutOptions | undefined {
  if (!layoutOptions) return undefined;

  let result: Record<string, unknown> | undefined;

  const clustering = layoutOptions.clustering;
  if (clustering && typeof clustering === "object") {
    const clusterBy = resolveClusterBy((clustering as Record<string, unknown>).clusterBy, nodes);
    if (clusterBy) {
      result = {
        ...layoutOptions,
        clustering: { ...(clustering as Record<string, unknown>), clusterBy },
      };
    }
  }

  const hierarchicalClusterBy = resolveClusterBy(layoutOptions.clusterBy, nodes);
  if (hierarchicalClusterBy) {
    result = { ...(result ?? layoutOptions), clusterBy: hierarchicalClusterBy };
  }

  return (result ?? layoutOptions) as LayoutOptions;
}
