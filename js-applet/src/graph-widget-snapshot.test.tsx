import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import NVL, { type ExternalCallbacks } from "@neo4j-nvl/base";

/**
 * Tests for the static PNG fallback: the snapshot the frontend sends once the layout
 * settles (and, debounced, after changes), and the hiding of the image output it
 * produces in a live frontend.
 *
 * As in graph-widget-save.test.tsx, the real NVL cannot run in jsdom, so the mounted
 * tests swap `InteractiveNvlWrapper` for a stub that installs a fake NVL and captures
 * the lifecycle callbacks the wrapper would normally own.
 */

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

import widget, { hideFallbackImage } from "./graph-widget";
import { createLocalModel } from "./local-model";

const PNG_DATA_URL = "data:image/png;base64,AAA";

function fakeNvl(overrides: Record<string, unknown> = {}): NVL {
  return {
    isLayoutMoving: () => false,
    getImageDataUrl: () => PNG_DATA_URL,
    ...overrides,
  } as unknown as NVL;
}

type WidgetState = {
  nodes: Array<{ id: string; caption?: string; properties: Record<string, unknown> }>;
  relationships: Array<{
    id: string;
    from: string;
    to: string;
    properties: Record<string, unknown>;
  }>;
  options: { layout: "d3Force"; showLayoutButton: boolean };
  height: string;
  width: string;
  theme: "light";
  selected: { nodeIds: string[]; relationshipIds: string[] };
  legend: { nodes: unknown; relationships: unknown; visible: boolean };
  fallback?: boolean;
  _nvl_ready?: boolean;
};

type CommModel = ReturnType<typeof createLocalModel<WidgetState>> & {
  send: (content: unknown) => void;
  sent: unknown[];
};

async function renderWidget(options: { fallback?: boolean } = {}): Promise<{
  model: CommModel;
  teardown: void | (() => void | Promise<void>) | (() => Promise<void>);
}> {
  const el = document.createElement("div");
  document.body.appendChild(el);

  const base = createLocalModel<WidgetState>({
    nodes: [{ id: "n1", caption: "Node 1", properties: {} }],
    relationships: [{ id: "r1", from: "n1", to: "n1", properties: {} }],
    options: { layout: "d3Force", showLayoutButton: true },
    height: "400px",
    width: "600px",
    theme: "light",
    selected: { nodeIds: [], relationshipIds: [] },
    legend: { nodes: null, relationships: null, visible: true },
    fallback: options.fallback ?? true,
  });

  const sent: unknown[] = [];
  const model = {
    ...base,
    send: (content: unknown) => {
      sent.push(content);
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

  return { model, teardown };
}

async function teardownWidget(
  teardown: void | (() => void | Promise<void>) | (() => Promise<void>),
): Promise<void> {
  if (typeof teardown === "function") await teardown();
}

afterEach(() => {
  document.body.innerHTML = "";
  nvlState.nvl = null;
  nvlState.callbacks = null;
  vi.restoreAllMocks();
});

describe("static PNG fallback", () => {
  it("sends a snapshot once the layout settles", async () => {
    nvlState.nvl = fakeNvl();
    const { model, teardown } = await renderWidget();

    try {
      act(() => nvlState.callbacks?.onLayoutDone?.());

      await vi.waitFor(() => {
        expect(model.sent).toEqual([{ kind: "snapshot", dataUrl: PNG_DATA_URL }]);
      });
    } finally {
      await teardownWidget(teardown);
    }
  });

  it("sends the snapshot with the graph's background color", async () => {
    const getImageDataUrl = vi.fn((_options: { backgroundColor?: string } = {}) => PNG_DATA_URL);
    nvlState.nvl = fakeNvl({ getImageDataUrl });
    const { teardown } = await renderWidget();

    try {
      act(() => nvlState.callbacks?.onLayoutDone?.());

      await vi.waitFor(() => expect(getImageDataUrl).toHaveBeenCalled());
      expect(getImageDataUrl.mock.calls[0]?.[0]).toHaveProperty("backgroundColor");
    } finally {
      await teardownWidget(teardown);
    }
  });

  it("refreshes the snapshot after the graph changes", async () => {
    nvlState.nvl = fakeNvl();
    const { model, teardown } = await renderWidget();

    try {
      act(() => nvlState.callbacks?.onLayoutDone?.());
      await vi.waitFor(() => expect(model.sent).toHaveLength(1));

      act(() => {
        model.set("nodes", [
          { id: "n1", caption: "Node 1", properties: {} },
          { id: "n2", caption: "Node 2", properties: {} },
        ]);
      });

      await vi.waitFor(() => expect(model.sent).toHaveLength(2));
    } finally {
      await teardownWidget(teardown);
    }
  });

  it("does not snapshot when the fallback is disabled", async () => {
    const getImageDataUrl = vi.fn(() => PNG_DATA_URL);
    nvlState.nvl = fakeNvl({ getImageDataUrl });
    const { model, teardown } = await renderWidget({ fallback: false });

    try {
      act(() => nvlState.callbacks?.onLayoutDone?.());
      await new Promise((resolve) => setTimeout(resolve, 700));

      expect(model.sent).toEqual([]);
      expect(getImageDataUrl).not.toHaveBeenCalled();
    } finally {
      await teardownWidget(teardown);
    }
  });

  it("does not snapshot while the layout is still moving", async () => {
    const getImageDataUrl = vi.fn(() => PNG_DATA_URL);
    nvlState.nvl = fakeNvl({ isLayoutMoving: () => true, getImageDataUrl });
    const { model, teardown } = await renderWidget();

    try {
      await new Promise((resolve) => setTimeout(resolve, 700));

      expect(model.sent).toEqual([]);
      expect(getImageDataUrl).not.toHaveBeenCalled();
    } finally {
      await teardownWidget(teardown);
    }
  });

  it("hides the stored image output once it reaches the DOM", async () => {
    nvlState.nvl = fakeNvl();
    const { model, teardown } = await renderWidget();

    try {
      act(() => nvlState.callbacks?.onLayoutDone?.());
      await vi.waitFor(() => expect(model.sent).toHaveLength(1));

      const output = document.createElement("div");
      output.className = "jp-OutputArea-child";
      const img = document.createElement("img");
      img.setAttribute("src", PNG_DATA_URL);
      output.appendChild(img);
      document.body.appendChild(output);

      await vi.waitFor(() => expect(output.style.display).toBe("none"));
    } finally {
      await teardownWidget(teardown);
    }
  });
});

describe("hideFallbackImage", () => {
  let cleanups: Array<() => void> = [];

  // Register the cleanup so an observer from one test cannot hide an image in the next.
  const hide = (widgetEl: HTMLElement, src: string): void => {
    cleanups.push(hideFallbackImage(widgetEl, src));
  };

  afterEach(() => {
    cleanups.forEach((cleanup) => cleanup());
    cleanups = [];
  });

  it("hides the whole output row in JupyterLab", () => {
    document.body.innerHTML = `
      <div class="jp-OutputArea">
        <div class="jp-OutputArea-child" id="image-output"><img src="${PNG_DATA_URL}"></div>
        <div class="jp-OutputArea-child"><div id="widget"></div></div>
      </div>`;
    const widgetEl = document.getElementById("widget") as HTMLElement;

    hide(widgetEl, PNG_DATA_URL);

    expect((document.getElementById("image-output") as HTMLElement).style.display).toBe("none");
  });

  it("hides the image itself when there is no JupyterLab output row", () => {
    document.body.innerHTML = `<img src="${PNG_DATA_URL}">`;
    const widgetEl = document.createElement("div");
    document.body.appendChild(widgetEl);

    hide(widgetEl, PNG_DATA_URL);

    expect((document.querySelector("img") as HTMLElement).style.display).toBe("none");
  });

  it("hides an image that only appears later", async () => {
    const widgetEl = document.createElement("div");
    document.body.appendChild(widgetEl);

    hide(widgetEl, PNG_DATA_URL);
    const img = document.createElement("img");
    img.setAttribute("src", PNG_DATA_URL);
    document.body.appendChild(img);

    await vi.waitFor(() => expect(img.style.display).toBe("none"));
  });

  it("leaves images with a different source alone", async () => {
    const widgetEl = document.createElement("div");
    document.body.appendChild(widgetEl);

    hide(widgetEl, PNG_DATA_URL);
    const img = document.createElement("img");
    img.setAttribute("src", "data:image/png;base64,OTHER");
    document.body.appendChild(img);

    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(img.style.display).toBe("");
  });

  it("stops watching after its timeout", async () => {
    vi.useFakeTimers();
    try {
      const widgetEl = document.createElement("div");
      document.body.appendChild(widgetEl);

      hide(widgetEl, PNG_DATA_URL);
      vi.advanceTimersByTime(10_001);

      const img = document.createElement("img");
      img.setAttribute("src", PNG_DATA_URL);
      document.body.appendChild(img);

      await Promise.resolve();
      expect(img.style.display).toBe("");
    } finally {
      vi.useRealTimers();
    }
  });
});
