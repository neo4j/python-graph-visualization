import widget, { type Theme, type WidgetData } from "./graph-widget";

/**
 * Streamlit Components v2 entrypoint for two-way rendering inside a Streamlit app.
 *
 * Streamlit does not support the Jupyter/anywidget comm protocol, so the notebook
 * `GraphWidget` can't be embedded directly (the community bridge streamlit-anywidget
 * also ignores traitlets `to_json`/`from_json` serializers, see
 * https://github.com/mdrazak2001/streamlit-anywidget/issues/6). Instead we reuse the
 * exact same React component via a small model shim and bridge state over Streamlit's
 * `st.components.v2.component` contract:
 *
 *   Python  --(get_state, respects to_json)-->  `data` prop
 *   Python  <--(set_state, respects from_json)-- setStateValue("selected"/"options", ...)
 *
 * The module's default export is the v2 mount function. It receives
 * `{ data, key, parentElement, setStateValue, ... }`. v2 mounts inline in the host
 * DOM (a shadow root when `isolate_styles=True`), and re-invokes this function with
 * fresh `data` whenever the data changes -- WITHOUT running the previous cleanup. So
 * we mount React exactly once per container and update it in place on later invokes,
 * avoiding a full remount (and graph relayout) of this heavy component.
 */

// ── The v2 component object passed to the default export ─────────────────────
type ComponentArg = {
  name: string;
  data: Partial<WidgetData> | null;
  key: string;
  parentElement: ShadowRoot | HTMLElement;
  setStateValue: (name: string, value: unknown) => void;
  setTriggerValue: (name: string, value: unknown) => void;
};

// ── Read-write anywidget model shim ─────────────────────────────────────────
// Backs `@anywidget/react`'s `useModelState`/`createRender`, which only rely on
// get / set / save_changes / on / off. Writes from the React component are pushed
// back to Python via setStateValue; updates coming from Python (`applyIncoming`)
// emit `change:` events to refresh React but are not echoed back, avoiding loops.
type Listener = (...args: unknown[]) => void;

// Traits the frontend is allowed to write back to Python. Mirror the two-way traits
// on GraphWidget (`selected` and `options`) and `_RECEIVE_KEYS` in streamlit.py.
const WRITABLE_KEYS: (keyof WidgetData)[] = ["selected", "options", "last_double_click"];

class StreamlitModel {
  private state: Partial<WidgetData> = {};
  private listeners = new Map<string, Set<Listener>>();
  private pending = new Set<keyof WidgetData>();

  constructor(private setStateValue: (name: string, value: unknown) => void) {}

  get<K extends keyof WidgetData>(key: K): WidgetData[K] {
    return this.state[key] as WidgetData[K];
  }

  set<K extends keyof WidgetData>(key: K, value: WidgetData[K]): void {
    this.state[key] = value;
    if (WRITABLE_KEYS.includes(key)) this.pending.add(key);
    this.emit(key);
  }

  save_changes(): void {
    for (const key of this.pending) this.setStateValue(key, this.state[key]);
    this.pending.clear();
  }

  on(event: string, cb: Listener): void {
    const key = event.startsWith("change:") ? event.slice("change:".length) : event;
    if (!this.listeners.has(key)) this.listeners.set(key, new Set());
    this.listeners.get(key)!.add(cb);
  }

  off(event: string, cb?: Listener): void {
    const key = event.startsWith("change:") ? event.slice("change:".length) : event;
    const set = this.listeners.get(key);
    if (!set) return;
    if (cb) set.delete(cb);
    else set.clear();
  }

  private emit(key: keyof WidgetData): void {
    this.listeners.get(key as string)?.forEach((cb) => cb());
    this.listeners.get("change")?.forEach((cb) => cb());
  }

  /** Seed initial state silently (before the React mount reads it). */
  initialize(incoming: Partial<WidgetData>): void {
    this.state = { ...incoming };
  }

  /**
   * Apply state pushed from Python without echoing it back. Only keys whose
   * serialized value actually changed emit a `change:` event, so React re-renders
   * exactly once and there's no feedback loop.
   */
  applyIncoming(incoming: Partial<WidgetData>): void {
    for (const rawKey of Object.keys(incoming) as (keyof WidgetData)[]) {
      const next = incoming[rawKey];
      const prev = this.state[rawKey];
      if (JSON.stringify(next) === JSON.stringify(prev)) continue;
      (this.state as Record<string, unknown>)[rawKey] = next;
      this.emit(rawKey);
    }
  }
}

// ── Theme: v2 exposes the Streamlit theme only as CSS custom properties on the
// host, so (unlike VS Code/Marimo) there is no class to sniff. Resolve "auto" from
// the host's `--st-background-color` brightness. ────────────────────────────────
function hostElement(parentElement: ShadowRoot | HTMLElement): HTMLElement {
  return parentElement instanceof ShadowRoot ? (parentElement.host as HTMLElement) : parentElement;
}

function resolveStreamlitTheme(host: HTMLElement): "light" | "dark" | null {
  const bg = getComputedStyle(host).getPropertyValue("--st-background-color").trim();
  const rgb = bg.match(/\d+/g);
  if (!rgb || rgb.length < 3) return null;
  const brightness = Number(rgb[0]) * 0.2126 + Number(rgb[1]) * 0.7152 + Number(rgb[2]) * 0.0722;
  return brightness < 128 ? "dark" : "light";
}

/** Replace a "auto" theme with the concrete Streamlit theme when we can detect it. */
function withResolvedTheme(data: Partial<WidgetData>, host: HTMLElement): Partial<WidgetData> {
  if ((data.theme ?? "auto") !== "auto") return data;
  const resolved = resolveStreamlitTheme(host);
  return resolved ? { ...data, theme: resolved as Theme } : data;
}

type Mounted = {
  model: StreamlitModel;
  host: HTMLElement;
  el: HTMLElement;
  width: string;
  height: string;
  dispose: () => void;
};

// One mounted React instance per container. The shadow root / host element is stable
// across v2 re-invocations for the same component instance, so we key on it.
const mounts = new WeakMap<ShadowRoot | HTMLElement, Mounted>();

export default function render(component: ComponentArg): () => void {
  const { data, parentElement, setStateValue } = component;
  const host = hostElement(parentElement);
  const incoming = withResolvedTheme(data ?? {}, host);

  const width = incoming.width ?? "100%";
  const height = incoming.height ?? "600px";

  let mounted = mounts.get(parentElement);

  // NVL reads its container size once at construction and exposes no resize API (and
  // doesn't observe container resizes), so a width/height change can't be applied to
  // the live instance — we must re-initialize the graph at the new size. This only
  // happens when the dimensions actually change; other updates (nodes, selection,
  // options) are applied in place below.
  if (mounted && (mounted.width !== width || mounted.height !== height)) {
    mounted.dispose();
    mounted = undefined;
  }

  if (!mounted) {
    const model = new StreamlitModel(setStateValue);
    model.initialize(incoming);

    const el = document.createElement("div");
    // Size the container before mounting so NVL initializes at the correct size.
    el.style.width = width;
    el.style.height = height;
    parentElement.appendChild(el);

    const unmount = widget.render({ model, el } as unknown as Parameters<typeof widget.render>[0]);

    // Re-resolve the theme when Streamlit toggles it (the `--st-*` vars change on
    // the host element's inline style).
    const observer = new MutationObserver(() => {
      model.applyIncoming(withResolvedTheme({ theme: "auto" }, host));
    });
    observer.observe(host, { attributes: true, attributeFilter: ["style", "class"] });

    const dispose = () => {
      observer.disconnect();
      Promise.resolve(unmount).then((fn) => (typeof fn === "function" ? fn() : undefined));
      el.remove();
      mounts.delete(parentElement);
    };

    mounted = { model, host, el, width, height, dispose };
    mounts.set(parentElement, mounted);
  } else {
    mounted.model.applyIncoming(incoming);
  }

  return mounted.dispose;
}
