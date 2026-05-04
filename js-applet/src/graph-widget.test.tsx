import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { act } from "react";
import { afterEach, describe, expect, it } from "vitest";
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
  teardown: void | (() => void | Promise<void>) | (() => Promise<void>);
};

async function renderWidget(
  overrides: Partial<WidgetState["options"]> = {}
): Promise<RenderedWidget> {
  const el = document.createElement("div");
  document.body.appendChild(el);

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
  });

  let teardown: RenderedWidget["teardown"] = undefined;
  await act(async () => {
    teardown = await widget.render({
      el,
      model: model as never,
      experimental: {} as never,
    });
  });

  return { el, teardown };
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
});
