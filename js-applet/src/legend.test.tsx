import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { Legend, LegendData } from "./legend";

afterEach(() => {
  document.body.innerHTML = "";
});

describe("Legend", () => {
  it("renders discrete swatch rows with labels and colors", () => {
    const legend: LegendData = {
      nodes: {
        title: "label",
        colorSpace: "discrete",
        entries: [
          { label: "Movies", color: "#0000ff" },
          { label: "Directors", color: "#ff0000" },
        ],
      },
      visible: true,
    };

    const { container } = render(<Legend legend={legend} />);

    expect(screen.getByText("Movies")).toBeTruthy();
    expect(screen.getByText("Directors")).toBeTruthy();

    const swatches = container.querySelectorAll<HTMLElement>(".nvl-legend-swatch");
    expect(swatches.length).toBe(2);
    // jsdom normalizes hex to rgb.
    expect(swatches[0]!.style.backgroundColor).toBe("rgb(0, 0, 255)");
    expect(swatches[1]!.style.backgroundColor).toBe("rgb(255, 0, 0)");
  });

  it("renders a gradient bar with min/max labels for continuous colorings", () => {
    const legend: LegendData = {
      nodes: {
        title: "score",
        colorSpace: "continuous",
        gradient: ["#000000", "#ffffff"],
        minValue: "10",
        maxValue: "30",
      },
    };

    const { container } = render(<Legend legend={legend} />);

    const bar = container.querySelector<HTMLElement>(".nvl-legend-gradient");
    expect(bar).toBeTruthy();
    expect(bar!.style.background).toContain("linear-gradient");
    expect(screen.getByText("10")).toBeTruthy();
    expect(screen.getByText("30")).toBeTruthy();
  });

  it("renders both node and relationship sections", () => {
    const legend: LegendData = {
      nodes: {
        title: "Node label",
        colorSpace: "discrete",
        entries: [{ label: "Movies", color: "#0000ff" }],
      },
      relationships: {
        title: "Rel type",
        colorSpace: "discrete",
        entries: [{ label: "ACTED_IN", color: "#00ff00" }],
      },
    };

    render(<Legend legend={legend} />);

    expect(screen.getByText("Node label")).toBeTruthy();
    expect(screen.getByText("Rel type")).toBeTruthy();
    expect(screen.getByText("Movies")).toBeTruthy();
    expect(screen.getByText("ACTED_IN")).toBeTruthy();
  });

  it("renders nothing when not visible", () => {
    const legend: LegendData = {
      nodes: {
        colorSpace: "discrete",
        entries: [{ label: "Movies", color: "#0000ff" }],
      },
      visible: false,
    };

    const { container } = render(<Legend legend={legend} />);

    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when both sections are empty", () => {
    const { container } = render(
      <Legend legend={{ nodes: null, relationships: null, visible: true }} />
    );

    expect(container.firstChild).toBeNull();
  });

  it("collapses and expands the body when the header is clicked", () => {
    const legend: LegendData = {
      nodes: {
        colorSpace: "discrete",
        entries: [{ label: "Movies", color: "#0000ff" }],
      },
    };

    render(<Legend legend={legend} />);

    expect(screen.getByText("Movies")).toBeTruthy();

    const toggle = screen.getByRole("button", { name: /legend/i });
    fireEvent.click(toggle);
    expect(screen.queryByText("Movies")).toBeNull();

    fireEvent.click(toggle);
    expect(screen.getByText("Movies")).toBeTruthy();
  });

  it("styles chrome from Needle theme tokens so it tracks light/dark", () => {
    const legend: LegendData = {
      nodes: {
        colorSpace: "discrete",
        entries: [{ label: "Movies", color: "#0000ff" }],
      },
    };

    const { container } = render(<Legend legend={legend} />);
    const panel = container.querySelector<HTMLElement>(".nvl-legend");
    expect(panel).toBeTruthy();
    // Chrome is driven by the theme-aware NDL tokens, not a hardcoded palette.
    expect(panel!.style.background).toContain("--theme-color-neutral-bg-default");
    expect(panel!.style.color).toContain("--theme-color-neutral-text-default");
    // the swatch label is reachable within the panel
    expect(within(panel!).getByText("Movies")).toBeTruthy();
  });
});
