import { describe, expect, it } from "vitest";
import type { SerializedNode } from "./data-transforms";
import { buildLayoutOptions } from "./layout-options";

const nodes: SerializedNode[] = [
  { id: "1", properties: { community: "a" } },
  { id: "2", properties: { community: "a" } },
  { id: "3", properties: { community: "b" } },
  { id: "4", properties: {} },
];

describe("buildLayoutOptions", () => {
  it("returns undefined when there are no layout options", () => {
    expect(buildLayoutOptions(undefined, nodes)).toBeUndefined();
  });

  it("passes options through unchanged when there is no clustering spec", () => {
    const layoutOptions = { gravity: 0.5 };
    expect(buildLayoutOptions(layoutOptions, nodes)).toBe(layoutOptions);
  });

  it("resolves a force-directed clustering property name into a function", () => {
    const result = buildLayoutOptions({ clustering: { clusterBy: "community" } }, nodes);
    const clusterBy = (result as { clustering: { clusterBy: (id: string) => unknown } }).clustering
      .clusterBy;

    expect(typeof clusterBy).toBe("function");
    expect(clusterBy("1")).toBe("a");
    expect(clusterBy("3")).toBe("b");
    // Nodes missing the property are independent.
    expect(clusterBy("4")).toBeUndefined();
    expect(clusterBy("missing")).toBeUndefined();
  });

  it("keeps the other clustering fields", () => {
    const result = buildLayoutOptions(
      { clustering: { clusterBy: "community", drawOutline: true, drawHalo: true } },
      nodes,
    );
    expect(result).toMatchObject({ clustering: { drawOutline: true, drawHalo: true } });
  });

  it("resolves a hierarchical clustering property name into a function", () => {
    const result = buildLayoutOptions({ clusterBy: "community" }, nodes);
    const clusterBy = (result as { clusterBy: (id: string) => unknown }).clusterBy;

    expect(typeof clusterBy).toBe("function");
    expect(clusterBy("2")).toBe("a");
  });

  it("leaves an already-resolved clusterBy function untouched", () => {
    const fn = () => "x";
    const layoutOptions = { clustering: { clusterBy: fn } };
    expect(buildLayoutOptions(layoutOptions, nodes)).toBe(layoutOptions);
  });
});
