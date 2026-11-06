import "@neo4j-ndl/base/lib/neo4j-ds-styles.css";
import type { NeoNode, NeoRel, PortableProperty } from "@neo4j-ndl/react-graph";
import type { Node, Relationship } from "@neo4j-nvl/base";
import { ICON_REGISTRY } from "./icon-registry";

export type SerializedNode = { properties: Record<string, unknown> } & Node;

// Absolute URLs (http:, https:, data:, ...) are used as-is; anything else is a
// catalog name looked up in the built-in icon registry.
const URL_SCHEME = /^[a-z][a-z0-9+.-]*:/i;
const normalizeIconName = (name: string): string => name.toLowerCase().replace(/[^a-z0-9]/g, "");

const ICON_LOOKUP = new Map(
  Object.entries(ICON_REGISTRY).map(([name, uri]) => [normalizeIconName(name), uri]),
);

/** Resolve a catalog icon name to its bundled data URI; pass URLs through unchanged. */
export function resolveIcon(value: string | undefined): string | undefined {
  if (!value) return undefined;
  if (URL_SCHEME.test(value)) return value;

  const uri = ICON_LOOKUP.get(normalizeIconName(value));
  if (!uri) {
    console.warn(`Unknown icon "${value}"; expected a name from the icon catalog or a URL.`);
    return undefined;
  }

  return uri;
}

function resolveOverlayIcon(
  overlayIcon: Node["overlayIcon"] | undefined,
  iconRefs: Record<string, string>,
): Node["overlayIcon"] | undefined {
  if (!overlayIcon) return undefined;

  const url = resolveIcon(expandIconRef(overlayIcon.url, iconRefs));
  return url ? { ...overlayIcon, url } : undefined;
}

// Large custom icons are sent once in `iconRefs` and referenced per entity by a
// `#<n>` key. `#` cannot start a URL or a catalog name, so it is a safe namespace.
function expandIconRef(
  value: string | undefined,
  iconRefs: Record<string, string>,
): string | undefined {
  if (!value) return undefined;
  if (value.startsWith("#")) return iconRefs[value];
  return value;
}

function isListOfStrings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

export function transformNodes(
  nodes: SerializedNode[],
  iconRefs: Record<string, string> = {},
): NeoNode[] {
  return nodes.map((node) => {
    const { icon, overlayIcon, ...rest } = node;
    const labelProperty = isListOfStrings(node.properties.labels) ? node.properties.labels : [];
    const resolvedIcon = resolveIcon(expandIconRef(icon, iconRefs));
    const resolvedOverlayIcon = resolveOverlayIcon(overlayIcon, iconRefs);
    return {
      ...rest,
      id: node.id,
      ...(resolvedIcon ? { icon: resolvedIcon } : {}),
      ...(resolvedOverlayIcon ? { overlayIcon: resolvedOverlayIcon } : {}),
      // This is done so that the overview panel breaks down by caption, rather than labels
      labels: node.caption ? [node.caption] : labelProperty,
      // Explicit `captions` (also when empty) overrides the NLG style engine's
      // auto-picked caption from node properties.
      captions: node.caption ? [{ value: node.caption }] : [],
      properties: Object.entries(node.properties).reduce<Record<string, PortableProperty>>(
        (acc, [key, value]) => {
          if (key === "labels") return acc;
          const type = typeof value;
          acc[key] = {
            stringified: type === "string" ? `"${value}"` : String(value),
            type,
          };
          return acc;
        },
        {},
      ),
    };
  });
}

export type SerializedRelationship = { properties: Record<string, unknown> } & Relationship;

export function transformRelationships(
  relationships: SerializedRelationship[],
  iconRefs: Record<string, string> = {},
): NeoRel[] {
  return relationships.map((rel) => {
    const { overlayIcon, ...rest } = rel;
    const resolvedOverlayIcon = resolveOverlayIcon(overlayIcon, iconRefs);
    return {
      ...rest,
      id: rel.id,
      ...(resolvedOverlayIcon ? { overlayIcon: resolvedOverlayIcon } : {}),
      type: rel.caption ?? (rel.properties.type as string | undefined) ?? "",
      properties: Object.entries(rel.properties).reduce<Record<string, PortableProperty>>(
        (acc, [key, value]) => {
          if (key === "type") return acc;
          acc[key] = {
            stringified: String(value),
            type: typeof value,
          };
          return acc;
        },
        {},
      ),
      from: rel.from,
      to: rel.to,
    };
  });
}
