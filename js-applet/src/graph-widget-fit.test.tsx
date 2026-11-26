import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import NVL, { type ExternalCallbacks } from "@neo4j-nvl/base";

/**
 * Tests for the Python `GraphWidget.fit()` round trip and the initial framing: the
 * `msg:custom` listener wiring in graph-widget.tsx, the exported `handleFitRequest`, the
 * fit applied once the layout settles, and the takeover of the wrapper's own default
 * auto-fit.
 *
 * As in graph-widget-save.test.tsx, the real NVL cannot run under jsdom, so the mounted
 * tests replace `InteractiveNvlWrapper` with a stub that installs a per-test fake NVL and
 * captures the lifecycle callbacks.
 */

// Per-test stand-in for the NVL instance and lifecycle callbacks the wrapper
// would normally create.
const nvlState = vi.hoisted(() => ({
  nvl: null as NVL | null,
  callbacks: null as ExternalCallbacks | null,
}));

vi.mock("@neo4j-nvl/react", async () => {
  const actual = await vi.importActual<typeof import("@neo4j-nvl/react")>("@neo4j-nvl/react");
  return {
    ...actual,
    InteractiveNvlWrapper: ({
      ref,
      nvlCallbacks,
    }: {
      ref?: { current: NVL | null };
      nvlCallbacks?: ExternalCallbacks;
    }) => {
      if (ref) ref.current = nvlState.nvl;
      nvlState.callbacks = nvlCallbacks ?? null;
      return null;
    },
  };
});

import widget, { handleFitRequest } from "./graph-widget";
import { createLocalModel } from "./local-model";

const NODE_IDS = ["n1", "n2"];

function fakeNvl(overrides: Record<string, unknown> = {}): NVL {
  return {
    isLayoutMoving: () => false,
    getNodes: () => NODE_IDS.map((id) => ({ id, x: 0, y: 0 })),
    ...overrides,
  } as unknown as NVL;
}

type WidgetOptions = {
  layout: "d3Force" | "hierarchical";
  showLayoutButton: boolean;
  showSearchButton?: boolean;
  zoom?: number;
  pan?: { x: number; y: number };
  fit?: boolean;
  fitNodeIds?: string[];
};

type WidgetState = {
  nodes: Array<{ id: string; caption?: string; properties: Record<string, unknown> }>;
  relationships: Array<{
    id: string;
    from: string;
    to: string;
    properties: Record<string, unknown>;
  }>;
  options: WidgetOptions;
  height: string;
  width: string;
  theme: "light" | "dark" | "auto";
  selected: { nodeIds: string[]; relationshipIds: string[] };
  legend: { nodes: unknown; relationships: unknown; visible: boolean };
  _nvl_ready?: boolean;
};

type CommModel = ReturnType<typeof createLocalModel<WidgetState>> & {
  send: (content: unknown) => void;
  sent: unknown[];
  emitCustom: (msg: unknown) => void;
};

async function renderWidgetWithCommModel(options?: Partial<WidgetOptions>): Promise<{
  el: HTMLDivElement;
  model: CommModel;
  teardown: void | (() => void | Promise<void>) | (() => Promise<void>);
}> {
  const el = document.createElement("div");
  document.body.appendChild(el);

  const base = createLocalModel<WidgetState>({
    nodes: [{ id: "n1", caption: "Node 1", properties: {} }],
    relationships: [{ id: "r1", from: "n1", to: "n1", properties: {} }],
    options: { layout: "d3Force", showLayoutButton: true, showSearchButton: true, ...options },
    height: "400px",
    width: "600px",
    theme: "light",
    selected: { nodeIds: [], relationshipIds: [] },
    legend: { nodes: null, relationships: null, visible: true },
  });

  const customListeners = new Set<(msg: unknown) => void>();
  const sent: unknown[] = [];
  const model = {
    ...base,
    on: (event: string, listener: () => void) => {
      if (event === "msg:custom") {
        customListeners.add(listener as (msg: unknown) => void);
      } else {
        base.on(event, listener);
      }
    },
    off: (event: string, listener: () => void) => {
      if (event === "msg:custom") {
        customListeners.delete(listener as (msg: unknown) => void);
      } else {
        base.off(event, listener);
      }
    },
    send: (content: unknown) => {
      sent.push(content);
    },
    emitCustom: (msg: unknown) => {
      customListeners.forEach((listener) => listener(msg));
    },
    sent,
  } as unknown as CommModel;

  let teardown: void | (() => void | Promise<void>) | (() => Promise<void>) = undefined;
  await act(async () => {
    teardown = await widget.render({
      el,
      model: model as never,
      signal: new AbortController().signal,
      host: {} as never,
      experimental: {} as never,
    });
  });

  return { el, model, teardown };
}

afterEach(() => {
  document.body.innerHTML = "";
  nvlState.nvl = null;
  nvlState.callbacks = null;
  vi.restoreAllMocks();
});

describe("handleFitRequest", () => {
  const reply = vi.fn<(id: string, payload: { error?: string }) => void>();

  it("frames every node currently in the graph", () => {
    const fit = vi.fn();
    const nvl = {
      getNodes: () => [
        { id: "n1", x: 0, y: 0 },
        { id: "n2", x: 10, y: 20 },
      ],
      fit,
    } as unknown as NVL;

    handleFitRequest({ kind: "fit", id: "1" }, nvl, reply);

    // NVL's fit silently does nothing without node ids, so they must always be passed.
    expect(fit).toHaveBeenCalledWith(["n1", "n2"], undefined);
    expect(reply).toHaveBeenCalledWith("1", {});
  });

  it("frames only the given node ids", () => {
    const fit = vi.fn();
    const nvl = {
      getNodes: () => [
        { id: "n1", x: 0, y: 0 },
        { id: "n2", x: 10, y: 20 },
        { id: "n3", x: 30, y: 40 },
      ],
      fit,
    } as unknown as NVL;

    handleFitRequest({ kind: "fit", id: "1a", nodeIds: ["n2", "n3"] }, nvl, reply);

    expect(fit).toHaveBeenCalledWith(["n2", "n3"], undefined);
    expect(reply).toHaveBeenCalledWith("1a", {});
  });

  it("reports a subset that matches no node", () => {
    // Framing a different set than the one asked for is worse than refusing.
    const fit = vi.fn();
    const nvl = { getNodes: () => [{ id: "n1", x: 0, y: 0 }], fit } as unknown as NVL;

    handleFitRequest({ kind: "fit", id: "1d", nodeIds: ["gone"] }, nvl, reply);

    expect(fit).not.toHaveBeenCalled();
    expect(reply).toHaveBeenCalledWith("1d", {
      error: "none of the given node ids are in the graph",
    });
  });

  it("reports node ids that are not a list of strings", () => {
    const fit = vi.fn();
    const nvl = { getNodes: () => [{ id: "n1", x: 0, y: 0 }], fit } as unknown as NVL;

    handleFitRequest({ kind: "fit", id: "1e", nodeIds: [1, 2] }, nvl, reply);

    expect(fit).not.toHaveBeenCalled();
    expect(reply).toHaveBeenCalledWith("1e", {
      error: "the node ids to frame must be a list of strings",
    });
  });

  it("reports positions NVL cannot frame instead of claiming success", () => {
    // NVL gives up quietly when the positions yield no center, so the fit would otherwise
    // acknowledge a request that changed nothing.
    const fit = vi.fn();
    const nvl = {
      getNodes: () => [
        { id: "n1", x: Number.NaN, y: 0 },
        { id: "n2", x: 10, y: 20 },
      ],
      fit,
    } as unknown as NVL;

    handleFitRequest({ kind: "fit", id: "1b" }, nvl, reply);

    expect(fit).not.toHaveBeenCalled();
    expect(reply).toHaveBeenCalledWith("1b", { error: "the node positions are not finite" });
  });

  it("acknowledges an empty graph without fitting", () => {
    // Nothing to frame is not a failure: the graph may still be filled in later.
    const fit = vi.fn();
    const nvl = { getNodes: () => [], fit } as unknown as NVL;

    handleFitRequest({ kind: "fit", id: "1c" }, nvl, reply);

    expect(fit).not.toHaveBeenCalled();
    expect(reply).toHaveBeenCalledWith("1c", {});
  });

  it("replies with an error when the graph is not rendered yet", () => {
    handleFitRequest({ kind: "fit", id: "2" }, null, reply);

    expect(reply).toHaveBeenCalledWith("2", {
      error: "The graph is not rendered yet; display the widget before fitting.",
    });
  });

  it("replies with an error when fitting throws", () => {
    const nvl = {
      getNodes: () => [{ id: "n1", x: 0, y: 0 }],
      fit: () => {
        throw new Error("boom");
      },
    } as unknown as NVL;

    handleFitRequest({ kind: "fit", id: "3" }, nvl, reply);

    expect(reply).toHaveBeenCalledWith("3", { error: "boom" });
  });

  it("ignores messages that are not fit requests", () => {
    const nvl = { getNodes: () => [], fit: vi.fn() } as unknown as NVL;

    handleFitRequest("not-an-object", nvl, reply);
    handleFitRequest({ kind: "something_else", id: "1" }, nvl, reply);
    handleFitRequest({ kind: "fit" }, nvl, reply);

    expect(reply).not.toHaveBeenCalled();
  });
});

describe("mounted widget fit wiring", () => {
  it("applies a fit request from Python", async () => {
    const fit = vi.fn();
    nvlState.nvl = fakeNvl({ fit });
    const { model, teardown } = await renderWidgetWithCommModel();

    try {
      await act(async () => {
        model.emitCustom({ kind: "fit", id: "req-1" });
      });

      expect(fit).toHaveBeenCalledWith(NODE_IDS, undefined);
      expect(model.sent).toEqual([{ kind: "fit_response", id: "req-1" }]);
    } finally {
      if (typeof teardown === "function") await teardown();
    }
  });

  it("frames only the node ids from the request", async () => {
    const fit = vi.fn();
    nvlState.nvl = fakeNvl({ fit });
    const { model, teardown } = await renderWidgetWithCommModel();

    try {
      await act(async () => {
        model.emitCustom({ kind: "fit", id: "req-subset", nodeIds: ["n2"] });
      });

      expect(fit).toHaveBeenCalledWith(["n2"], undefined);
      expect(model.sent).toEqual([{ kind: "fit_response", id: "req-subset" }]);
    } finally {
      if (typeof teardown === "function") await teardown();
    }
  });

  it("replies with an error while the graph is not rendered", async () => {
    nvlState.nvl = null;
    const { model, teardown } = await renderWidgetWithCommModel();

    try {
      await act(async () => {
        model.emitCustom({ kind: "fit", id: "req-2" });
      });

      expect(model.sent).toEqual([
        {
          kind: "fit_response",
          id: "req-2",
          error: "The graph is not rendered yet; display the widget before fitting.",
        },
      ]);
    } finally {
      if (typeof teardown === "function") await teardown();
    }
  });

  it("frames the graph once the layout settles by default", async () => {
    const fit = vi.fn();
    nvlState.nvl = fakeNvl({ fit });
    const { teardown } = await renderWidgetWithCommModel();

    try {
      act(() => nvlState.callbacks?.onLayoutDone?.());

      // Instant, so the static PNG fallback captures the fitted view rather than one mid-transition.
      expect(fit).toHaveBeenCalledExactlyOnceWith(NODE_IDS, { animated: false });
    } finally {
      if (typeof teardown === "function") await teardown();
    }
  });

  it("logs when the initial framing cannot be applied", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const fit = vi.fn();
    nvlState.nvl = fakeNvl({ getNodes: () => [{ id: "n1", x: Number.NaN, y: 0 }], fit });
    const { teardown } = await renderWidgetWithCommModel();

    try {
      act(() => nvlState.callbacks?.onLayoutDone?.());

      // The widget still works, so this stays a warning rather than an error.
      expect(fit).not.toHaveBeenCalled();
      expect(warn).toHaveBeenCalledWith(
        "[neo4j-viz] Could not frame the graph:",
        expect.any(Error),
      );
    } finally {
      if (typeof teardown === "function") await teardown();
    }
  });

  it("does not log for a graph with no nodes", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    nvlState.nvl = fakeNvl({ getNodes: () => [], fit: vi.fn() });
    const { teardown } = await renderWidgetWithCommModel();

    try {
      act(() => nvlState.callbacks?.onLayoutDone?.());
      await new Promise((resolve) => setTimeout(resolve, 350));

      // An empty graph has nothing to frame, which is not a failure worth logging.
      expect(warn).not.toHaveBeenCalledWith(
        "[neo4j-viz] Could not frame the graph:",
        expect.anything(),
      );
    } finally {
      if (typeof teardown === "function") await teardown();
    }
  });

  it("frames only the configured node ids on the initial framing", async () => {
    const fit = vi.fn();
    nvlState.nvl = fakeNvl({ fit });
    const { teardown } = await renderWidgetWithCommModel({ fit: true, fitNodeIds: ["n2"] });

    try {
      act(() => nvlState.callbacks?.onLayoutDone?.());

      expect(fit).toHaveBeenCalledExactlyOnceWith(["n2"], { animated: false });
    } finally {
      if (typeof teardown === "function") await teardown();
    }
  });

  it("switches off the wrapper's own default auto-fit", async () => {
    nvlState.nvl = fakeNvl();
    const { teardown } = await renderWidgetWithCommModel();

    try {
      // react-graph registers a default `onLayoutComputing` fit unless the consumer overrides
      // it; passing `undefined` must survive its Object.assign merge and unregister it.
      expect(nvlState.callbacks?.onLayoutComputing).toBeUndefined();
    } finally {
      if (typeof teardown === "function") await teardown();
    }
  });

  it("does not frame the graph when fit is disabled", async () => {
    const fit = vi.fn();
    nvlState.nvl = fakeNvl({ fit });
    const { teardown } = await renderWidgetWithCommModel({ fit: false });

    try {
      act(() => nvlState.callbacks?.onLayoutDone?.());
      await new Promise((resolve) => setTimeout(resolve, 350));

      expect(fit).not.toHaveBeenCalled();
    } finally {
      if (typeof teardown === "function") await teardown();
    }
  });

  it("does not frame the graph when an explicit zoom is set", async () => {
    const fit = vi.fn();
    nvlState.nvl = fakeNvl({ fit });
    const { teardown } = await renderWidgetWithCommModel({ zoom: 1.5 });

    try {
      act(() => nvlState.callbacks?.onLayoutDone?.());
      await new Promise((resolve) => setTimeout(resolve, 350));

      expect(fit).not.toHaveBeenCalled();
    } finally {
      if (typeof teardown === "function") await teardown();
    }
  });

  it("does not frame the graph when an explicit pan is set", async () => {
    const fit = vi.fn();
    nvlState.nvl = fakeNvl({ fit });
    const { teardown } = await renderWidgetWithCommModel({ pan: { x: 1, y: 2 } });

    try {
      act(() => nvlState.callbacks?.onLayoutDone?.());
      await new Promise((resolve) => setTimeout(resolve, 350));

      expect(fit).not.toHaveBeenCalled();
    } finally {
      if (typeof teardown === "function") await teardown();
    }
  });
});
