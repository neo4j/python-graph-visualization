import widget from "./graph-widget";

/**
 * Wraps the graph widget for static HTML rendering.
 */

// Data is injected by Python (nvl.py) via window.__NEO4J_VIZ_DATA__
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const data: Record<string, any> =
  ((window as unknown as Record<string, unknown>).__NEO4J_VIZ_DATA__ as
    | Record<string, unknown>
    | undefined) ?? {};

// Model shim — mimics anywidget's model interface for the static HTML path.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const model: any = {
  get(key: string) {
    return data[key];
  },
  on() {},
  off() {},
  set() {},
  save_changes() {},
};

// Detect light/dark theme from page background
const bg = window
  .getComputedStyle(document.body)
  .getPropertyValue("background-color");
const rgb = bg.match(/\d+/g);

if (rgb) {
  const brightness =
    Number(rgb[0]) * 0.2126 + Number(rgb[1]) * 0.7152 + Number(rgb[2]) * 0.0722;
  document.documentElement.className = brightness < 128 ? "dark" : "light";
}

// Render the graph widget
const el = document.getElementById("neo4j-viz-container")!;
el.style.width = (data.width as string) ?? "100%";
el.style.height = (data.height as string) ?? "100vh";
// eslint-disable-next-line @typescript-eslint/no-explicit-any
widget.render({ model, el } as any);
