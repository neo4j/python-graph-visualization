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

function parseHexColor(color: string): [number, number, number] | undefined {
  const match = /^#?([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i.exec(color.trim());
  if (!match?.[1]) return undefined;

  let digits = match[1];
  if (digits.length === 3) {
    digits = digits
      .split("")
      .map((d) => d + d)
      .join("");
  }

  const value = Number.parseInt(digits.slice(0, 6), 16);
  return [(value >> 16) & 0xff, (value >> 8) & 0xff, value & 0xff];
}

function channelToLinear(channel: number): number {
  const s = channel / 255;
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
}

function relativeLuminance([r, g, b]: [number, number, number]): number {
  return 0.2126 * channelToLinear(r) + 0.7152 * channelToLinear(g) + 0.0722 * channelToLinear(b);
}

function contrastRatio(a: number, b: number): number {
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

// NVL picks the most readable of these two for a node's text/icon and inverts a
// black icon when it settles on white. Mirror that so overlays flip together with
// in-node icons on the same fill.
const DARK_GLYPH_LUMINANCE = relativeLuminance([0x1a, 0x1b, 0x1d]);
const LIGHT_GLYPH_LUMINANCE = relativeLuminance([0xff, 0xff, 0xff]);

/** Whether a fill is dark enough that NVL would invert a black icon to white. */
export function isDarkColor(color: string | undefined): boolean {
  if (!color) return false;

  const rgb = parseHexColor(color);
  if (!rgb) return false;

  const luminance = relativeLuminance(rgb);
  return (
    contrastRatio(luminance, DARK_GLYPH_LUMINANCE) < contrastRatio(luminance, LIGHT_GLYPH_LUMINANCE)
  );
}

// Catalog data URIs are percent-encoded SVG whose glyphs are black (`#000` -> `%23000`).
const BLACK_GLYPH = /%23(?:000000|000)(?![0-9a-fA-F])/gi;

function invertCatalogIcon(uri: string): string {
  return uri.replace(BLACK_GLYPH, "%23ffffff");
}

function resolveOverlayIcon(
  overlayIcon: Node["overlayIcon"] | undefined,
  iconRefs: Record<string, string>,
  isDark: boolean,
): Node["overlayIcon"] | undefined {
  if (!overlayIcon) return undefined;

  const value = expandIconRef(overlayIcon.url, iconRefs);
  if (!value) return undefined;

  // NVL never inverts overlay icons, so a black catalog overlay would be invisible
  // on a dark fill; use the white variant instead. Custom URLs and data URIs are
  // left as-is, so coloured badges keep their colour.
  if (isDark && !URL_SCHEME.test(value)) {
    const catalogUri = ICON_LOOKUP.get(normalizeIconName(value));
    if (catalogUri) return { ...overlayIcon, url: invertCatalogIcon(catalogUri) };
  }

  const url = resolveIcon(value);
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
    const resolvedOverlayIcon = resolveOverlayIcon(overlayIcon, iconRefs, isDarkColor(node.color));
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
    const resolvedOverlayIcon = resolveOverlayIcon(overlayIcon, iconRefs, isDarkColor(rel.color));
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
