import { describe, expect, it } from "vitest";
import {
  SerializedRelationship,
  transformNodes,
  transformRelationships,
  type SerializedNode,
} from "./data-transforms";

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
    const nodes: SerializedNode[] = [
      { id: "35", properties: { labels: ["User"] } },
    ];

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
      id: "35",
      labels: [],
      properties: {},
    });
  });
});
