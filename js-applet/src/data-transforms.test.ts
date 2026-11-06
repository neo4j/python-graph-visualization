import { describe, expect, it } from "vitest";
import {
  isDarkColor,
  resolveIcon,
  SerializedRelationship,
  transformNodes,
  transformRelationships,
  type SerializedNode,
} from "./data-transforms";
import { ICON_REGISTRY } from "./icon-registry";

describe("data-transforms", () => {
  it("should transform a node with a caption", () => {
    const nodes: SerializedNode[] = [
      {
        id: "35",
        caption: "5",
        properties: { componentId: "my_component_id" },
      },
    ];
    const result = transformNodes(nodes);
    expect(result).toHaveLength(1);

    expect(result[0]?.caption).toBe("5");
  });

  it("should support all node fields", () => {
    const nodes: SerializedNode[] = [
      {
        activated: true,
        caption: "5",
        captionAlign: "top",
        captionSize: 12,
        color: "red",
        disabled: true,
        hovered: true,
        id: "35",
        pinned: true,
        properties: { componentId: "my_component_id" },
        selected: true,
        size: 10,
        x: 1,
        y: 10,
      },
    ];
    const result = transformNodes(nodes);
    expect(result).toHaveLength(1);

    expect(result[0]).toEqual({
      activated: true,
      caption: "5",
      captionAlign: "top",
      captionSize: 12,
      captions: [{ value: "5" }],
      color: "red",
      disabled: true,
      hovered: true,
      id: "35",
      // labels have been populated from the caption property
      labels: ["5"],
      pinned: true,
      // properties have been transformed to the NeoNode properties format
      properties: {
        componentId: {
          stringified: '"my_component_id"',
          type: "string",
        },
      },
      selected: true,
      size: 10,
      x: 1,
      y: 10,
    });
  });

  it("should emit captions from the caption, not from properties", () => {
    const nodes: SerializedNode[] = [
      {
        id: "0",
        caption: "Person",
        color: "#e0e0e0",
        properties: { labels: ["Person"], centrality: 0.42 },
      },
    ];

    const result = transformNodes(nodes);

    expect(result[0]?.captions).toEqual([{ value: "Person" }]);
    expect(result[0]?.color).toBe("#e0e0e0");
  });

  it("should emit empty captions when no caption is set", () => {
    const nodes: SerializedNode[] = [
      { id: "0", properties: { labels: ["Person"], centrality: 0.42 } },
    ];

    const result = transformNodes(nodes);

    expect(result[0]?.captions).toEqual([]);
  });

  it("should transform a relationship with a caption", () => {
    const relationships: SerializedRelationship[] = [
      {
        id: "35",
        caption: "5",
        from: "36",
        to: "37",
        properties: { componentId: "my_component_id" },
      },
    ];
    const result = transformRelationships(relationships);
    expect(result).toHaveLength(1);
    expect(result[0]?.caption).toBe("5");
  });

  it("should support all relationship fields", () => {
    const relationships: SerializedRelationship[] = [
      {
        caption: "5",
        captionAlign: "top",
        captionSize: 12,
        color: "red",
        disabled: true,
        from: "36",
        hovered: true,
        id: "35",
        properties: { componentId: "my_component_id" },
        selected: true,
        to: "37",
        type: "HAS_COMPONENT",
        width: 10,
      },
    ];
    const result = transformRelationships(relationships);
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      caption: "5",
      captionAlign: "top",
      captionSize: 12,
      color: "red",
      disabled: true,
      from: "36",
      hovered: true,
      id: "35",
      properties: {
        componentId: {
          stringified: "my_component_id",
          type: "string",
        },
      },
      selected: true,
      to: "37",
      type: "5",
      width: 10,
    });
  });

  it("should respect exting labels", () => {
    const nodes: SerializedNode[] = [{ id: "35", properties: { labels: ["User"] } }];

    const result = transformNodes(nodes);
    expect(result).toHaveLength(1);
    expect(result[0]?.labels).toEqual(["User"]);
  });

  it("should stringify numbers", () => {
    const nodes: SerializedNode[] = [{ id: "35", properties: { age: 25 } }];
    const result = transformNodes(nodes);
    expect(result).toHaveLength(1);
    expect(result[0]?.properties.age).toEqual({
      stringified: "25",
      type: "number",
    });
  });

  it("handle if node has neither caption nor labels", () => {
    const nodes: SerializedNode[] = [{ id: "35", properties: {} }];
    const result = transformNodes(nodes);
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      captions: [],
      id: "35",
      labels: [],
      properties: {},
    });
  });

  it("should resolve a catalog icon name to its data URI", () => {
    const nodes: SerializedNode[] = [{ id: "0", icon: "Circle", properties: {} }];
    const result = transformNodes(nodes);
    expect(result[0]?.icon).toBe(ICON_REGISTRY.Circle);
  });

  it("should resolve catalog icon names case- and separator-insensitively", () => {
    expect(resolveIcon("database_check")).toBe(ICON_REGISTRY.DatabaseCheck);
    expect(resolveIcon("DatabaseCheck")).toBe(ICON_REGISTRY.DatabaseCheck);
    expect(resolveIcon("DATABASECHECK")).toBe(ICON_REGISTRY.DatabaseCheck);
  });

  it("should pass through URLs unchanged", () => {
    expect(resolveIcon("https://example.com/icon.svg")).toBe("https://example.com/icon.svg");
    expect(resolveIcon("data:image/svg+xml,%3Csvg%2F%3E")).toBe("data:image/svg+xml,%3Csvg%2F%3E");
  });

  it("should drop unknown icon names", () => {
    expect(resolveIcon("not-a-real-icon")).toBeUndefined();
    const result = transformNodes([{ id: "0", icon: "not-a-real-icon", properties: {} }]);
    expect(result[0]?.icon).toBeUndefined();
  });

  it("should resolve overlay icons on nodes and relationships", () => {
    const node = transformNodes([
      { id: "0", overlayIcon: { url: "Pin", position: [1, 1], size: 0.5 }, properties: {} },
    ])[0];
    expect(node?.overlayIcon).toEqual({ url: ICON_REGISTRY.Pin, position: [1, 1], size: 0.5 });

    const rel = transformRelationships([
      {
        id: "r",
        from: "0",
        to: "1",
        overlayIcon: { url: "https://example.com/b.svg" },
        properties: {},
      },
    ])[0];
    expect(rel?.overlayIcon).toEqual({ url: "https://example.com/b.svg" });
  });

  it("keeps the icon catalog within the size budget", () => {
    expect(Object.keys(ICON_REGISTRY).length).toBeLessThanOrEqual(100);
    expect(JSON.stringify(ICON_REGISTRY).length).toBeLessThan(120 * 1024);
  });

  it("should expand icon references from the shared table", () => {
    const iconRefs = { "#0": "data:image/svg+xml,%3Csvg%2F%3E" };
    const node = transformNodes([{ id: "0", icon: "#0", properties: {} }], iconRefs)[0];
    expect(node?.icon).toBe(iconRefs["#0"]);

    const rel = transformRelationships(
      [{ id: "r", from: "0", to: "1", overlayIcon: { url: "#0" }, properties: {} }],
      iconRefs,
    )[0];
    expect(rel?.overlayIcon).toEqual({ url: iconRefs["#0"] });
  });

  it("should drop unresolved icon references without warning", () => {
    const node = transformNodes([{ id: "0", icon: "#9", properties: {} }])[0];
    expect(node?.icon).toBeUndefined();
  });

  describe("overlay icon contrast", () => {
    it("inverts a catalog overlay icon on a dark fill", () => {
      const node = transformNodes([
        { id: "0", color: "#1a1a1a", overlayIcon: { url: "Pin" }, properties: {} },
      ])[0];

      expect(node?.overlayIcon?.url).toContain("%23ffffff");
      expect(node?.overlayIcon?.url).not.toContain("%23000");
    });

    it("keeps a catalog overlay icon black on a light fill", () => {
      const node = transformNodes([
        { id: "0", color: "#ffffff", overlayIcon: { url: "Pin" }, properties: {} },
      ])[0];

      expect(node?.overlayIcon?.url).toBe(ICON_REGISTRY.Pin);
    });

    it("keeps a catalog overlay icon black when no fill color is set", () => {
      const node = transformNodes([{ id: "0", overlayIcon: { url: "Pin" }, properties: {} }])[0];

      expect(node?.overlayIcon?.url).toBe(ICON_REGISTRY.Pin);
    });

    it("leaves custom overlay URLs untouched on a dark fill", () => {
      const url = "https://example.com/badge.svg";
      const node = transformNodes([
        { id: "0", color: "#1a1a1a", overlayIcon: { url }, properties: {} },
      ])[0];

      expect(node?.overlayIcon?.url).toBe(url);
    });

    it("leaves data-URI overlay icons untouched on a dark fill", () => {
      const iconRefs = { "#0": "data:image/svg+xml,%3Csvg%2F%3E" };
      const node = transformNodes(
        [{ id: "0", color: "#1a1a1a", overlayIcon: { url: "#0" }, properties: {} }],
        iconRefs,
      )[0];

      expect(node?.overlayIcon?.url).toBe(iconRefs["#0"]);
    });

    it("inverts a relationship overlay icon on a dark relationship", () => {
      const rel = transformRelationships([
        {
          id: "r",
          from: "0",
          to: "1",
          color: "#000000",
          overlayIcon: { url: "Pin" },
          properties: {},
        },
      ])[0];

      expect(rel?.overlayIcon?.url).toContain("%23ffffff");
    });

    it("mirrors NVL's contrast rule when deciding what is dark", () => {
      expect(isDarkColor("#000000")).toBe(true);
      expect(isDarkColor("#1a1a1a")).toBe(true);
      expect(isDarkColor("#800000")).toBe(true);
      expect(isDarkColor("#000")).toBe(true);
      expect(isDarkColor("#1a1a1a80")).toBe(true);
      expect(isDarkColor("#ffffff")).toBe(false);
      expect(isDarkColor("#abaa86")).toBe(false); // default node palette sample
      expect(isDarkColor("#959aa1")).toBe(false); // default relationship color
      expect(isDarkColor(undefined)).toBe(false);
      expect(isDarkColor("not-a-color")).toBe(false);
    });
  });
});
