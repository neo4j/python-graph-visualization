import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import NVL from "@neo4j-nvl/base";

/**
 * Tests for the Python `GraphWidget.save()` round trip: the `msg:custom`
 * listener wiring in graph-widget.tsx plus the exported `handleSaveRequest`.
 *
 * The real NVL cannot be driven from jsdom (its canvas renderers need a real
 * 2D/WebGL context, and under React StrictMode's double mount the recreated
 * instance fails to initialize), so the mounted tests replace
 * `InteractiveNvlWrapper` with a stub that installs a per-test fake NVL into
 * the widget's `nvlRef`. NVL's own image export is not under test here — only
 * our request/reply wiring on top of it.
 */

// Per-test stand-in for the NVL instance the wrapper would normally create.
const nvlState = vi.hoisted(() => ({ nvl: null as NVL | null }));

vi.mock("@neo4j-nvl/react", async () => {
  const actual = await vi.importActual<typeof import("@neo4j-nvl/react")>("@neo4j-nvl/react");
  return {
    ...actual,
    // Installs the fake NVL during render (no act()/effects needed — writing
    // the plain ref object during render is side-effect free here). React 19
    // passes `ref` as a regular prop, which is how react-graph hands over the
    // widget's nvlRef.
    InteractiveNvlWrapper: ({ ref }: { ref?: { current: NVL | null } }) => {
      if (ref) ref.current = nvlState.nvl;
      return null;
    },
  };
});

import widget, { handleSaveRequest } from "./graph-widget";
import { createLocalModel } from "./local-model";

type WidgetState = {
  nodes: Array<{ id: string; caption?: string; properties: Record<string, unknown> }>;
  relationships: Array<{
    id: string;
    from: string;
    to: string;
    properties: Record<string, unknown>;
  }>;
  options: {
    layout: "d3Force" | "hierarchical";
    showLayoutButton: boolean;
    showSearchButton?: boolean;
  };
  height: string;
  width: string;
  theme: "light" | "dark" | "auto";
  selected: { nodeIds: string[]; relationshipIds: string[] };
  legend: { nodes: unknown; relationships: unknown; visible: boolean };
};

// The kernel-less local model extended with the comm half of the anywidget
// protocol: a `send` back-channel (observable via `sent`) and "msg:custom"
// listeners that tests can trigger through `emitCustom`, as a notebook kernel
// would.
type CommModel = ReturnType<typeof createLocalModel<WidgetState>> & {
  send: (content: unknown) => void;
  sent: unknown[];
  emitCustom: (msg: unknown) => void;
};

async function renderWidgetWithCommModel(): Promise<{
  el: HTMLDivElement;
  model: CommModel;
  teardown: void | (() => void | Promise<void>) | (() => Promise<void>);
}> {
  const el = document.createElement("div");
  document.body.appendChild(el);

  const base = createLocalModel<WidgetState>({
    nodes: [{ id: "n1", caption: "Node 1", properties: {} }],
    relationships: [{ id: "r1", from: "n1", to: "n1", properties: {} }],
    options: { layout: "d3Force", showLayoutButton: true, showSearchButton: true },
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
  vi.restoreAllMocks();
});

describe("handleSaveRequest", () => {
  const reply = vi.fn<(id: string, payload: { dataUrl?: string; error?: string }) => void>();

  beforeEach(() => {
    reply.mockClear();
  });

  it("replies with the png data url", () => {
    const getImageDataUrl = vi.fn(() => "data:image/png;base64,AAA");
    const nvl = { getImageDataUrl } as unknown as NVL;

    handleSaveRequest({ kind: "save_request", id: "1", format: "png" }, nvl, reply);

    expect(getImageDataUrl).toHaveBeenCalledWith({});
    expect(reply).toHaveBeenCalledWith("1", { dataUrl: "data:image/png;base64,AAA" });
  });

  it("passes the background color through", () => {
    const getImageDataUrl = vi.fn(() => "data:image/png;base64,AAA");
    const nvl = { getImageDataUrl } as unknown as NVL;

    handleSaveRequest(
      { kind: "save_request", id: "1", format: "png", backgroundColor: "#ffffff" },
      nvl,
      reply,
    );

    expect(getImageDataUrl).toHaveBeenCalledWith({ backgroundColor: "#ffffff" });
    expect(reply).toHaveBeenCalledWith("1", { dataUrl: "data:image/png;base64,AAA" });
  });

  it("replies with an error when png generation throws", () => {
    const nvl = {
      getImageDataUrl: vi.fn(() => {
        throw new Error("boom");
      }),
    } as unknown as NVL;

    handleSaveRequest({ kind: "save_request", id: "1", format: "png" }, nvl, reply);

    expect(reply).toHaveBeenCalledWith("1", {
      error: "Failed to generate the PNG image: Error: boom",
    });
  });

  it("replies with the svg data url", async () => {
    const getSvgDataUrl = vi.fn(() =>
      Promise.resolve("data:image/svg+xml;charset=utf-8,%3Csvg%3E"),
    );
    const nvl = { getSvgDataUrl } as unknown as NVL;

    handleSaveRequest({ kind: "save_request", id: "2", format: "svg" }, nvl, reply);

    expect(getSvgDataUrl).toHaveBeenCalledWith({});
    await vi.waitFor(() => {
      expect(reply).toHaveBeenCalledWith("2", {
        dataUrl: "data:image/svg+xml;charset=utf-8,%3Csvg%3E",
      });
    });
  });

  it("replies with an error when svg generation rejects", async () => {
    const nvl = { getSvgDataUrl: vi.fn(() => Promise.reject(new Error("nope"))) } as unknown as NVL;

    handleSaveRequest({ kind: "save_request", id: "2", format: "svg" }, nvl, reply);

    await vi.waitFor(() => {
      expect(reply).toHaveBeenCalledWith("2", {
        error: "Failed to generate the SVG image: Error: nope",
      });
    });
  });

  it("replies with an error for an unknown format", () => {
    const nvl = {} as NVL;

    handleSaveRequest({ kind: "save_request", id: "3", format: "jpeg" }, nvl, reply);

    expect(reply).toHaveBeenCalledWith("3", { error: "Unknown save format: jpeg" });
  });

  it("replies with an error when the graph is not rendered yet", () => {
    handleSaveRequest({ kind: "save_request", id: "4", format: "png" }, null, reply);

    expect(reply).toHaveBeenCalledWith("4", {
      error: "The graph is not rendered yet; display the widget before saving.",
    });
  });

  it("ignores messages that are not save requests", () => {
    const nvl = {} as NVL;

    handleSaveRequest("not-an-object", nvl, reply);
    handleSaveRequest({ kind: "something_else", id: "1" }, nvl, reply);
    handleSaveRequest({ kind: "save_request" }, nvl, reply);

    expect(reply).not.toHaveBeenCalled();
  });
});

describe("mounted widget save wiring", () => {
  it("replies to a png save request with the rendered data url", async () => {
    const getImageDataUrl = vi.fn(() => "data:image/png;base64,AAA");
    nvlState.nvl = { getImageDataUrl } as unknown as NVL;
    const { model, teardown } = await renderWidgetWithCommModel();

    try {
      await act(async () => {
        model.emitCustom({ kind: "save_request", id: "req-1", format: "png" });
      });

      expect(getImageDataUrl).toHaveBeenCalledWith({});
      expect(model.sent).toEqual([
        { kind: "save_response", id: "req-1", dataUrl: "data:image/png;base64,AAA" },
      ]);
    } finally {
      if (typeof teardown === "function") await teardown();
    }
  });

  it("passes the background color from the request", async () => {
    const getImageDataUrl = vi.fn(() => "data:image/png;base64,AAA");
    nvlState.nvl = { getImageDataUrl } as unknown as NVL;
    const { model, teardown } = await renderWidgetWithCommModel();

    try {
      await act(async () => {
        model.emitCustom({
          kind: "save_request",
          id: "req-bg",
          format: "png",
          backgroundColor: "#ffffff",
        });
      });

      expect(getImageDataUrl).toHaveBeenCalledWith({ backgroundColor: "#ffffff" });
    } finally {
      if (typeof teardown === "function") await teardown();
    }
  });

  it("replies to an svg save request with the rendered data url", async () => {
    const getSvgDataUrl = vi.fn(() =>
      Promise.resolve("data:image/svg+xml;charset=utf-8,%3Csvg%3E"),
    );
    nvlState.nvl = { getSvgDataUrl } as unknown as NVL;
    const { model, teardown } = await renderWidgetWithCommModel();

    try {
      await act(async () => {
        model.emitCustom({ kind: "save_request", id: "req-2", format: "svg" });
      });

      expect(getSvgDataUrl).toHaveBeenCalledWith({});
      await vi.waitFor(() => {
        expect(model.sent).toEqual([
          {
            kind: "save_response",
            id: "req-2",
            dataUrl: "data:image/svg+xml;charset=utf-8,%3Csvg%3E",
          },
        ]);
      });
    } finally {
      if (typeof teardown === "function") await teardown();
    }
  });

  it("replies with an error while the graph is not rendered", async () => {
    nvlState.nvl = null;
    const { model, teardown } = await renderWidgetWithCommModel();

    try {
      await act(async () => {
        model.emitCustom({ kind: "save_request", id: "req-3", format: "png" });
      });

      expect(model.sent).toEqual([
        {
          kind: "save_response",
          id: "req-3",
          error: "The graph is not rendered yet; display the widget before saving.",
        },
      ]);
    } finally {
      if (typeof teardown === "function") await teardown();
    }
  });

  it("ignores custom messages that are not save requests", async () => {
    const getImageDataUrl = vi.fn();
    nvlState.nvl = { getImageDataUrl } as unknown as NVL;
    const { model, teardown } = await renderWidgetWithCommModel();

    try {
      await act(async () => {
        model.emitCustom({ kind: "unrelated", id: "x" });
        model.emitCustom("not-an-object");
      });

      expect(model.sent).toEqual([]);
      expect(getImageDataUrl).not.toHaveBeenCalled();
    } finally {
      if (typeof teardown === "function") await teardown();
    }
  });
});
