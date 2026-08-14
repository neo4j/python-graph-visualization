import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { act, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@neo4j-ndl/react", async () => {
  const actual =
    await vi.importActual<typeof import("@neo4j-ndl/react")>("@neo4j-ndl/react");

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
  nodes: Array<{ id: string; caption?: string; properties: Record<string, unknown> }>;
  relationships: Array<{ id: string; from: string; to: string; properties: Record<string, unknown> }>;
  options: {
    layout: "d3Force" | "hierarchical";
    showLayoutButton: boolean;
  };
  height: string;
  width: string;
  theme: "light" | "dark" | "auto";
  selected: { nodeIds: string[]; relationshipIds: string[] };
  legend: {
    nodes?: { colorSpace?: string; title?: string; entries?: Array<{ label: string; color: string }> } | null;
    relationships?: { colorSpace?: string; title?: string; entries?: Array<{ label: string; color: string }> } | null;
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
  overrides: Partial<WidgetState> = {}
): Promise<RenderedWidget> {
  const el = document.createElement("div");
  document.body.appendChild(el);

  const defaultNodes = [{ id: "n1", caption: "Node 1", properties: {} }];
  const defaultRelationships = [
    { id: "r1", from: "n1", to: "n1", properties: {} },
  ];

  const model = createLocalModel<WidgetState>({
    nodes: overrides.nodes ?? defaultNodes,
    relationships: overrides.relationships ?? defaultRelationships,
    options: {
      layout: "d3Force",
      showLayoutButton: true,
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
  overrides: Partial<WidgetState["options"]> = {}
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
      expect(
        shadowRoot.querySelector('[data-neo4j-viz-ndl-shadow-root]')
      ).toBeTruthy();

      expect(
        document.head.querySelector('[data-neo4j-viz-ndl-overlays]')
      ).toBeTruthy();
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
        expect(
          screen.getByTestId("needle-theme-provider").getAttribute("data-theme")
        ).toBe("light");
      });

      await act(async () => {
        document.body.className = "dark-theme";
      });

      await waitFor(() => {
        expect(
          screen.getByTestId("needle-theme-provider").getAttribute("data-theme")
        ).toBe("dark");
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
        expect(
          screen.getByTestId("needle-theme-provider").getAttribute("data-theme")
        ).toBe("light");
      });

      await act(async () => {
        document.body.className = "light-theme";
      });

      await waitFor(() => {
        expect(
          screen.getByTestId("needle-theme-provider").getAttribute("data-theme")
        ).toBe("light");
      });
    } finally {
      if (typeof teardown === "function") {
        await teardown();
      }
    }
  });
});
