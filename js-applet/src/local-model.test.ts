import { describe, expect, it, vi } from "vitest";
import { createLocalModel } from "./local-model";

type State = {
  selected: { nodeIds: string[]; relationshipIds: string[] };
  theme: "light" | "dark";
};

const initial = (): Partial<State> => ({
  selected: { nodeIds: [], relationshipIds: [] },
  theme: "light",
});

describe("createLocalModel", () => {
  it("returns the current value from get", () => {
    const model = createLocalModel<State>(initial());
    expect(model.get("theme")).toBe("light");
    expect(model.get("selected")).toEqual({ nodeIds: [], relationshipIds: [] });
  });

  // Regression guard for GDS-286: a no-op `set` froze controlled props such as
  // `selected`, so clicking a node in the static HTML could never select it.
  it("updates state on set and notifies change listeners", () => {
    const model = createLocalModel<State>(initial());
    const listener = vi.fn();
    model.on("change:selected", listener);

    const next = { nodeIds: ["n1"], relationshipIds: [] };
    model.set("selected", next);

    expect(model.get("selected")).toBe(next);
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("only notifies listeners for the changed key", () => {
    const model = createLocalModel<State>(initial());
    const selectedListener = vi.fn();
    const themeListener = vi.fn();
    model.on("change:selected", selectedListener);
    model.on("change:theme", themeListener);

    model.set("theme", "dark");

    expect(themeListener).toHaveBeenCalledTimes(1);
    expect(selectedListener).not.toHaveBeenCalled();
  });

  it("stops notifying a listener after off", () => {
    const model = createLocalModel<State>(initial());
    const listener = vi.fn();
    model.on("change:selected", listener);
    model.off("change:selected", listener);

    model.set("selected", { nodeIds: ["n1"], relationshipIds: [] });

    expect(listener).not.toHaveBeenCalled();
  });

  it("returns a stable reference from get until the next set (useSyncExternalStore contract)", () => {
    const model = createLocalModel<State>(initial());
    const first = model.get("selected");
    expect(model.get("selected")).toBe(first);

    const next = { nodeIds: ["n1"], relationshipIds: [] };
    model.set("selected", next);
    expect(model.get("selected")).toBe(next);
    expect(model.get("selected")).toBe(next);
  });
});
