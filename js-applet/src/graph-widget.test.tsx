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
};

class FakeModel {
  private readonly listeners = new Map<string, Set<() => void>>();

  constructor(private readonly state: WidgetState) {}

  get<K extends keyof WidgetState>(key: K): WidgetState[K] {
    return this.state[key];
  }

  set<K extends keyof WidgetState>(key: K, value: WidgetState[K]): void {
    this.state[key] = value;
    this.listeners.get(`change:${String(key)}`)?.forEach((listener) => listener());
  }

  on(event: string, listener: () => void): void {
    const listeners = this.listeners.get(event) ?? new Set<() => void>();
    listeners.add(listener);
    this.listeners.set(event, listeners);
  }

  off(event: string, listener: () => void): void {
    this.listeners.get(event)?.delete(listener);
  }

  save_changes(): void {}
}

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

  const model = new FakeModel({
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
  });

  let teardown: RenderedWidget["teardown"] = undefined;
  await act(async () => {
    teardown = await widget.render({
      el,
      model: model as never,
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

  const model = new FakeModel({
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
  });

  let teardown: RenderedWidget["teardown"] = undefined;
  await act(async () => {
    teardown = await widget.render({
      el,
      model: model as never,
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
