import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { act, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@neo4j-ndl/react", async () => {
  const actual = await vi.importActual<typeof import("@neo4j-ndl/react")>("@neo4j-ndl/react");

  return {
    ...actual,
    NeedleThemeProvider: ({
      theme,
      children,
    }: {
      theme: "light" | "dark";
      children: ReactNode;
    }) => (
      <div data-testid="needle-theme-provider" data-theme={theme}>
        {children}
      </div>
    ),
  };
});

import widget from "./graph-widget";
import { createLocalModel } from "./local-model";

type WidgetState = {
  nodes: Array<{
    id: string;
    caption?: string;
    color?: string;
    properties: Record<string, unknown>;
  }>;
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
    selectionMode?: "single" | "box" | "lasso";
  };
  height: string;
  width: string;
  theme: "light" | "dark" | "auto";
  selected: { nodeIds: string[]; relationshipIds: string[] };
  legend: {
    nodes?: {
      colorSpace?: string;
      title?: string;
      entries?: Array<{ label: string; color: string }>;
    } | null;
    relationships?: {
      colorSpace?: string;
      title?: string;
      entries?: Array<{ label: string; color: string }>;
    } | null;
    visible?: boolean;
  };
};

// The static HTML render path uses the real `createLocalModel` shim, so tests
// exercise it directly rather than a hand-rolled fake — this keeps the shim's
// contract (notably `set` emitting change events, see GDS-286) under test.
type FakeModel = ReturnType<typeof createLocalModel<WidgetState>>;

type RenderedWidget = {
  el: HTMLDivElement;
  model: FakeModel;
  teardown: void | (() => void | Promise<void>) | (() => Promise<void>);
};

async function renderWidget(
  overrides: Omit<Partial<WidgetState>, "options"> & {
    options?: Partial<WidgetState["options"]>;
  } = {},
): Promise<RenderedWidget> {
  const el = document.createElement("div");
  document.body.appendChild(el);

  const defaultNodes = [{ id: "n1", caption: "Node 1", properties: {} }];
  const defaultRelationships = [{ id: "r1", from: "n1", to: "n1", properties: {} }];

  const model = createLocalModel<WidgetState>({
    nodes: overrides.nodes ?? defaultNodes,
    relationships: overrides.relationships ?? defaultRelationships,
    options: {
      layout: "d3Force",
      showLayoutButton: true,
      showSearchButton: true,
      ...(overrides.options ?? {}),
    },
    height: overrides.height ?? "400px",
    width: overrides.width ?? "600px",
    theme: overrides.theme ?? "light",
    selected: overrides.selected ?? { nodeIds: [], relationshipIds: [] },
    legend: overrides.legend ?? { nodes: null, relationships: null, visible: true },
  });

  let teardown: RenderedWidget["teardown"] = undefined;
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

async function renderWidgetInShadowRoot(
  overrides: Partial<WidgetState["options"]> = {},
): Promise<RenderedWidget & { host: HTMLDivElement; shadowRoot: ShadowRoot }> {
  const host = document.createElement("div");
  document.body.appendChild(host);
  const shadowRoot = host.attachShadow({ mode: "open" });
  const el = document.createElement("div");
  shadowRoot.appendChild(el);

  const model = createLocalModel<WidgetState>({
    nodes: [{ id: "n1", caption: "Node 1", properties: {} }],
    relationships: [{ id: "r1", from: "n1", to: "n1", properties: {} }],
    options: {
      layout: "d3Force",
      showLayoutButton: true,
      showSearchButton: true,
      ...overrides,
    },
    height: "400px",
    width: "600px",
    theme: "light",
    selected: { nodeIds: [], relationshipIds: [] },
    legend: { nodes: null, relationships: null, visible: true },
  });

  let teardown: RenderedWidget["teardown"] = undefined;
  await act(async () => {
    teardown = await widget.render({
      el,
      model: model as never,
      signal: new AbortController().signal,
      host: {} as never,
      experimental: {} as never,
    });
  });

  return { el, host, shadowRoot, model, teardown };
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("graph-widget button testing", () => {
  it("opens the layout selector menu when the layout button is clicked", async () => {
    const { el, teardown } = await renderWidget();

    try {
      await waitFor(() => {
        expect(within(el).getByRole("button", { name: /select layout/i })).toBeTruthy();
      });

      await act(async () => {
        fireEvent.click(within(el).getByRole("button", { name: /select layout/i }));
      });

      expect(await screen.findByText("Force-based layout")).toBeTruthy();
    } finally {
      if (typeof teardown === "function") {
        await teardown();
      }
    }
  });

  it("opens the download menu when the download button is clicked", async () => {
    const { el, teardown } = await renderWidget();

    try {
      await waitFor(() => {
        expect(within(el).getByRole("button", { name: /download/i })).toBeTruthy();
      });

      await act(async () => {
        fireEvent.click(within(el).getByRole("button", { name: /download/i }));
      });

      expect(await screen.findByText("Download as PNG")).toBeTruthy();
    } finally {
      if (typeof teardown === "function") {
        await teardown();
      }
    }
  });

  it("renders the search button when enabled", async () => {
    const { el, teardown } = await renderWidget();

    try {
      await waitFor(() => {
        expect(within(el).getByRole("button", { name: "Search" })).toBeTruthy();
      });
    } finally {
      if (typeof teardown === "function") {
        await teardown();
      }
    }
  });

  it("hides the search button when disabled", async () => {
    const { el, teardown } = await renderWidget({ options: { showSearchButton: false } });

    try {
      await waitFor(() => {
        expect(within(el).getByRole("button", { name: /download/i })).toBeTruthy();
      });

      expect(within(el).queryByRole("button", { name: "Search" })).toBeNull();
    } finally {
      if (typeof teardown === "function") {
        await teardown();
      }
    }
  });

  it("expands the search input when the search button is clicked", async () => {
    const { el, teardown } = await renderWidget();

    try {
      const searchButton = await waitFor(() => within(el).getByRole("button", { name: "Search" }));

      await act(async () => {
        fireEvent.click(searchButton);
      });

      expect(within(el).getByPlaceholderText("Search...")).toBeTruthy();
    } finally {
      if (typeof teardown === "function") {
        await teardown();
      }
    }
  });

  it("types a search term and clears it back to no highlight", async () => {
    const { el, teardown } = await renderWidget();

    try {
      const searchButton = await waitFor(() => within(el).getByRole("button", { name: "Search" }));

      await act(async () => {
        fireEvent.click(searchButton);
      });

      const input = within(el).getByPlaceholderText("Search...") as HTMLInputElement;

      await act(async () => {
        fireEvent.change(input, { target: { value: "Node 1" } });
      });
      expect(input.value).toBe("Node 1");

      await act(async () => {
        fireEvent.click(within(el).getByRole("button", { name: "Clear search" }));
      });
      expect(input.value).toBe("");
    } finally {
      if (typeof teardown === "function") {
        await teardown();
      }
    }
  });

  it("renders with an initial selection sourced from the model", async () => {
    const { el, model, teardown } = await renderWidget({
      selected: { nodeIds: ["n1"], relationshipIds: [] },
    });

    try {
      await waitFor(() => {
        expect(within(el).getByRole("button", { name: /download/i })).toBeTruthy();
      });

      // The selection is controlled by the model and left untouched on initial render.
      expect(model.get("selected")).toEqual({
        nodeIds: ["n1"],
        relationshipIds: [],
      });
    } finally {
      if (typeof teardown === "function") {
        await teardown();
      }
    }
  });

  it("re-syncs the gesture when the model's selectionMode changes", async () => {
    const { el, model, teardown } = await renderWidget();

    try {
      const gestureButton = await waitFor(() =>
        within(el).getByRole("button", { name: /select gesture/i }),
      );

      await act(async () => {
        fireEvent.click(gestureButton);
      });

      const individualOption = await screen.findByRole("menuitemradio", { name: /Individual/ });
      expect(individualOption.getAttribute("aria-checked")).toBe("true");

      await act(async () => {
        model.set("options", {
          layout: "d3Force",
          showLayoutButton: true,
          showSearchButton: true,
          selectionMode: "box",
        });
      });

      await waitFor(() => {
        expect(
          screen.getByRole("menuitemradio", { name: /Box/ }).getAttribute("aria-checked"),
        ).toBe("true");
      });
      expect(
        screen.getByRole("menuitemradio", { name: /Individual/ }).getAttribute("aria-checked"),
      ).toBe("false");
    } finally {
      if (typeof teardown === "function") {
        await teardown();
      }
    }
  });

  it("renders a non-empty legend sourced from the model", async () => {
    const { el, teardown } = await renderWidget({
      legend: {
        nodes: {
          colorSpace: "discrete",
          title: "label",
          entries: [{ label: "Movies", color: "#569480" }],
        },
        relationships: null,
        visible: true,
      },
    });

    try {
      await waitFor(() => {
        expect(within(el).getByText("Movies")).toBeTruthy();
      });
    } finally {
      if (typeof teardown === "function") {
        await teardown();
      }
    }
  });

  it("toggles the legend overlay via its island button", async () => {
    const { el, teardown } = await renderWidget({
      legend: {
        nodes: {
          colorSpace: "discrete",
          entries: [{ label: "Movies", color: "#569480" }],
        },
        relationships: null,
        visible: true,
      },
    });

    try {
      // Auto-shown when a legend is available.
      await waitFor(() => {
        expect(within(el).getByText("Movies")).toBeTruthy();
      });

      const toggle = within(el).getByRole("button", { name: "Toggle legend" });
      await act(async () => {
        fireEvent.click(toggle);
      });
      expect(within(el).queryByText("Movies")).toBeNull();

      await act(async () => {
        fireEvent.click(toggle);
      });
      expect(within(el).getByText("Movies")).toBeTruthy();
    } finally {
      if (typeof teardown === "function") {
        await teardown();
      }
    }
  });

  it("renders no legend panel when the legend is empty", async () => {
    const { el, teardown } = await renderWidget();

    try {
      await waitFor(() => {
        expect(within(el).getByRole("button", { name: /download/i })).toBeTruthy();
      });

      expect(el.querySelector(".nvl-legend")).toBeNull();
    } finally {
      if (typeof teardown === "function") {
        await teardown();
      }
    }
  });

  it("re-renders the legend when the model's legend trait changes", async () => {
    const { el, model, teardown } = await renderWidget();

    try {
      await waitFor(() => {
        expect(within(el).getByRole("button", { name: /download/i })).toBeTruthy();
      });
      expect(el.querySelector(".nvl-legend")).toBeNull();

      await act(async () => {
        model.set("legend", {
          nodes: {
            colorSpace: "discrete",
            entries: [{ label: "Directors", color: "#c990c0" }],
          },
          relationships: null,
          visible: true,
        });
      });

      await waitFor(() => {
        expect(within(el).getByText("Directors")).toBeTruthy();
      });
    } finally {
      if (typeof teardown === "function") {
        await teardown();
      }
    }
  });

  it("bridges NDL styles to document.head when rendered inside a shadow root", async () => {
    const { shadowRoot, teardown } = await renderWidgetInShadowRoot();

    try {
      expect(shadowRoot.querySelector("[data-neo4j-viz-ndl-shadow-root]")).toBeTruthy();

      expect(document.head.querySelector("[data-neo4j-viz-ndl-overlays]")).toBeTruthy();
    } finally {
      if (typeof teardown === "function") {
        await teardown();
      }
    }
  });

  it("updates the resolved theme when host theme classes change after mount", async () => {
    document.body.className = "light-theme";

    const { teardown } = await renderWidget({ theme: "auto" });

    try {
      await waitFor(() => {
        expect(screen.getByTestId("needle-theme-provider").getAttribute("data-theme")).toBe(
          "light",
        );
      });

      await act(async () => {
        document.body.className = "dark-theme";
      });

      await waitFor(() => {
        expect(screen.getByTestId("needle-theme-provider").getAttribute("data-theme")).toBe("dark");
      });
    } finally {
      if (typeof teardown === "function") {
        await teardown();
      }
    }
  });

  it("keeps an explicit light theme fixed when host theme classes change", async () => {
    document.body.className = "dark-theme";

    const { teardown } = await renderWidget({ theme: "light" });

    try {
      await waitFor(() => {
        expect(screen.getByTestId("needle-theme-provider").getAttribute("data-theme")).toBe(
          "light",
        );
      });

      await act(async () => {
        document.body.className = "light-theme";
      });

      await waitFor(() => {
        expect(screen.getByTestId("needle-theme-provider").getAttribute("data-theme")).toBe(
          "light",
        );
      });
    } finally {
      if (typeof teardown === "function") {
        await teardown();
      }
    }
  });
});

describe("graph-widget rendering", () => {
  it("draws node colors and captions from the widget data (GDS-355)", async () => {
    // jsdom reports 0x0 for every element, which makes NVL skip drawing entirely,
    // so element sizes are forced while the widget is mounted.
    const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
    Element.prototype.getBoundingClientRect = function () {
      return {
        x: 0,
        y: 0,
        top: 0,
        left: 0,
        right: 600,
        bottom: 400,
        width: 600,
        height: 400,
        toJSON: () => ({}),
      };
    };
    const sizeProperties = ["offsetWidth", "offsetHeight", "clientWidth", "clientHeight"] as const;
    const originalDescriptors = sizeProperties.map(
      (prop) => [prop, Object.getOwnPropertyDescriptor(HTMLElement.prototype, prop)] as const,
    );
    for (const prop of sizeProperties) {
      Object.defineProperty(HTMLElement.prototype, prop, {
        configurable: true,
        get: () => (prop.endsWith("Width") ? 600 : 400),
      });
    }

    // The synchronous requestAnimationFrame stub from the setup makes NVL's
    // layout/draw loop stall, so frames are scheduled asynchronously instead.
    let frameCount = 0;
    const originalRequestAnimationFrame = globalThis.requestAnimationFrame;
    globalThis.requestAnimationFrame = ((callback: FrameRequestCallback) => {
      if (++frameCount > 400) {
        return 0;
      }
      setTimeout(() => callback(Date.now()), 0);
      return frameCount;
    }) as typeof globalThis.requestAnimationFrame;

    const fillStyles: string[] = [];
    const measuredTexts: string[] = [];
    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (
      this: HTMLCanvasElement,
    ): CanvasRenderingContext2D {
      if (!this.width) {
        this.width = 600;
      }
      if (!this.height) {
        this.height = 400;
      }
      const target: Record<string, unknown> = {
        canvas: this,
        measureText: (text: string) => {
          measuredTexts.push(text);
          return { width: String(text).length * 6 };
        },
      };
      return new Proxy(target, {
        get(t, prop) {
          const key = prop as string;
          if (key === "fillStyle" || key === "strokeStyle") {
            return t[key];
          }
          if (typeof t[key] !== "undefined") {
            return t[key];
          }
          return () => {
            if (key === "fill" || key === "stroke") {
              fillStyles.push(String(t.fillStyle));
            }
            return undefined;
          };
        },
        set(t, prop, value) {
          t[prop as string] = value;
          if (prop === "fillStyle" && typeof value === "string") {
            fillStyles.push(value);
          }
          return true;
        },
      }) as unknown as CanvasRenderingContext2D;
    } as unknown as typeof HTMLCanvasElement.prototype.getContext;

    const { teardown } = await renderWidget({
      nodes: [
        {
          id: "0",
          caption: "Person",
          color: "#e0e0e0",
          properties: { labels: ["Person"], centrality: 0.1 },
        },
        {
          id: "1",
          caption: "Movie",
          color: "#000000",
          properties: { labels: ["Movie"], centrality: 0.9 },
        },
      ],
      relationships: [{ id: "r0", from: "0", to: "1", properties: {} }],
    });

    try {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 100));
      });

      expect(fillStyles.length).toBeGreaterThan(0);
      expect(fillStyles).toContain("#e0e0e0");
      expect(fillStyles).toContain("#000000");

      expect(measuredTexts).toContain("Person");
      expect(measuredTexts).toContain("Movie");
      expect(measuredTexts).not.toContain("0.1");
      expect(measuredTexts).not.toContain("0.9");
    } finally {
      if (typeof teardown === "function") {
        await teardown();
      }

      globalThis.requestAnimationFrame = originalRequestAnimationFrame;
      Element.prototype.getBoundingClientRect = originalGetBoundingClientRect;
      for (const [prop, descriptor] of originalDescriptors) {
        if (descriptor) {
          Object.defineProperty(HTMLElement.prototype, prop, descriptor);
        }
      }
      HTMLCanvasElement.prototype.getContext = originalGetContext;
    }
  });
});
