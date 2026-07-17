import { createRender, useModelState } from "@anywidget/react";
import ndlCssText from "@neo4j-ndl/base/lib/neo4j-ds-styles.css?inline";
import { Gesture, GraphSelection, GraphVisualization } from "@neo4j-ndl/react-graph";
import type NVL from "@neo4j-nvl/base";
import type { Layout, NvlOptions } from "@neo4j-nvl/base";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  SerializedNode,
  SerializedRelationship,
  transformNodes,
  transformRelationships,
} from "./data-transforms";
import { hasLegendContent, Legend, LegendData } from "./legend";
import { GraphErrorBoundary } from "./graph-error-boundary";
import { Divider, IconButton, IconButtonArray, NeedleThemeProvider } from "@neo4j-ndl/react";
import { SwatchIconOutline } from "@neo4j-ndl/react/icons";

export type Theme = "dark" | "light" | "auto";

export type GraphOptions = {
  layout: Layout;
  nvlOptions?: Partial<NvlOptions>;
  zoom?: number;
  pan?: { x: number; y: number };
  layoutOptions?: Record<string, unknown>;
  showLayoutButton: boolean;
  selectionMode?: Gesture;
};

export type DoubleClickEvent = {
  kind: "node" | "relationship";
  id: string;
};

export type WidgetData = {
  nodes: SerializedNode[];
  relationships: SerializedRelationship[];
  options: GraphOptions;
  height: string;
  width: string;
  theme: Theme;
  selected: GraphSelection;
  legend: LegendData;
  last_double_click: DoubleClickEvent | null;
};

const EMPTY_SELECTION: GraphSelection = { nodeIds: [], relationshipIds: [] };
const EMPTY_LEGEND: LegendData = {
  nodes: null,
  relationships: null,
  visible: true,
};

function detectTheme(): "light" | "dark" {
  if (
    document.body.classList.contains("vscode-light") ||
    document.body.classList.contains("light-theme")
  ) {
    return "light";
  }
  if (
    document.body.classList.contains("vscode-dark") ||
    document.body.classList.contains("dark-theme")
  ) {
    return "dark";
  }

  const backgroundColorString = window
    .getComputedStyle(document.body, null)
    .getPropertyValue("background-color");
  const colorsArray = backgroundColorString.match(/\d+/g);
  if (!colorsArray || colorsArray.length < 3) {
    return "light";
  }
  const brightness =
    Number(colorsArray[0]) * 0.2126 +
    Number(colorsArray[1]) * 0.7152 +
    Number(colorsArray[2]) * 0.0722;

  // VSCode reports: rgba(0, 0, 0, 0) as the background color independent of the theme, default to light here
  if (brightness === 0 && colorsArray.length > 3 && colorsArray[3] === "0") {
    return "light";
  }

  return brightness < 128 ? "dark" : "light";
}

function resolveTheme(theme: Theme): "light" | "dark" {
  return theme === "auto" ? detectTheme() : theme;
}

function useResolvedTheme(theme: Theme | undefined): "light" | "dark" {
  const normalizedTheme = theme ?? "auto";
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">(() =>
    resolveTheme(normalizedTheme),
  );

  useEffect(() => {
    if (normalizedTheme !== "auto") {
      setResolvedTheme(normalizedTheme);
      return;
    }

    const updateTheme = () => {
      const nextTheme = detectTheme();
      setResolvedTheme((currentTheme) => (currentTheme === nextTheme ? currentTheme : nextTheme));
    };

    updateTheme();

    if (typeof MutationObserver === "undefined") {
      return;
    }

    const observer = new MutationObserver(updateTheme);
    const observerOptions = {
      attributes: true,
      attributeFilter: ["class", "style"],
    } satisfies MutationObserverInit;

    observer.observe(document.documentElement, observerOptions);
    observer.observe(document.body, observerOptions);

    return () => observer.disconnect();
  }, [normalizedTheme]);

  return resolvedTheme;
}

// @font-face rules in shadow DOM adopted stylesheets don't register fonts at the
// document level, so the browser can't find them for rendering. We extract and hoist
// them into document.head eagerly at module load so fonts begin loading immediately.
const fontFaceRules = (ndlCssText.match(/@font-face\s*\{[^}]*\}/g) || []).join("\n");
if (fontFaceRules) {
  const fontStyle = document.createElement("style");
  fontStyle.textContent = fontFaceRules;
  document.head.appendChild(fontStyle);
}

const documentStyleSelector = "[data-neo4j-viz-ndl-main]";
const overlayStyleSelector = "[data-neo4j-viz-ndl-overlays]";
const shadowRootStyleSelector = "[data-neo4j-viz-ndl-shadow-root]";

function appendStyle(root: Node & ParentNode, attributeName: string, cssText: string) {
  const style = document.createElement("style");
  style.setAttribute(attributeName, "true");
  style.textContent = cssText;
  root.appendChild(style);
}

/**
 * Injects the full NDL stylesheet into the appropriate scope. In shadow DOM
 * contexts (e.g. Marimo notebooks), widget content stays styled inside the
 * shadow root and portaled overlays get the same stylesheet in document.head.
 */
function injectNdlCss(el: HTMLElement) {
  const rootNode = el.getRootNode();
  if (rootNode instanceof ShadowRoot) {
    if (!rootNode.querySelector(shadowRootStyleSelector)) {
      appendStyle(rootNode, "data-neo4j-viz-ndl-shadow-root", ndlCssText);
    }

    if (!document.head.querySelector(overlayStyleSelector)) {
      appendStyle(document.head, "data-neo4j-viz-ndl-overlays", ndlCssText);
    }

    return;
  }

  if (!document.head.querySelector(documentStyleSelector)) {
    appendStyle(document.head, "data-neo4j-viz-ndl-main", ndlCssText);
  }
}

function GraphWidget() {
  const [nodes] = useModelState<WidgetData["nodes"]>("nodes");
  const [relationships] = useModelState<WidgetData["relationships"]>("relationships");
  const [options, setOptions] = useModelState<WidgetData["options"]>("options");
  const [height] = useModelState<WidgetData["height"]>("height");
  const [width] = useModelState<WidgetData["width"]>("width");
  const [theme] = useModelState<WidgetData["theme"]>("theme");
  const [selected, setSelected] = useModelState<WidgetData["selected"]>("selected");
  const [, setLastDoubleClick] =
    useModelState<WidgetData["last_double_click"]>("last_double_click");
  const [legend] = useModelState<WidgetData["legend"]>("legend");
  const { layout, nvlOptions, zoom, pan, layoutOptions, showLayoutButton, selectionMode } =
    options ?? {};
  // `gesture` is locally controlled so the GestureSelectButton stays interactive, but it is
  // seeded from (and re-synced to) the Python-provided `selectionMode` when that changes.
  const [gesture, setGesture] = useState<Gesture>(selectionMode ?? "single");
  useEffect(() => {
    if (selectionMode) setGesture(selectionMode);
  }, [selectionMode]);
  const setLayout = (layout: Layout) => {
    setOptions({ ...options, layout });
  };

  const wrapperRef = useRef<HTMLDivElement>(null);
  const nvlRef = useRef<NVL | null>(null);
  const resolvedTheme = useResolvedTheme(theme);

  useEffect(() => {
    if (!wrapperRef.current) return;
    injectNdlCss(wrapperRef.current);
  }, []);

  // NVL sizes its <canvas> once at mount via an internal `element-resize-event` scroll-sensor
  // polyfill that doesn't fire when the side panel (NDL Drawer, type "push") flex-shrinks its
  // container — so the canvas keeps its initial width and clicks land offset by the panel width
  // (#417). NVL has no public resize API, so we bridge a real ResizeObserver to that polyfill: on
  // any size change we dispatch a synthetic `scroll` on the container, which the polyfill listens
  // for (capture) and uses to recompute the canvas size. TEMPORARY SHIM — remove once the upstream
  // NVL resize fix (see changelog/PR) is bumped into this package.
  //
  // NVL may replace its container element after mount (observed in the Streamlit/Components-v2
  // mount flow), so a one-shot observer would stick to a detached element. We watch the stable
  // wrapper subtree with a MutationObserver and re-attach the ResizeObserver whenever the
  // current container (`getContainer()`) changes.
  useEffect(() => {
    if (!wrapperRef.current) return;
    let ro: ResizeObserver | undefined;
    let observed: HTMLElement | null = null;
    let raf = 0;
    let attempts = 0;
    let disposed = false;

    // The polyfill is only safe to poke while it's live: on NVL destroy it sets
    // `__resizeTriggers__` to `false` and (due to a capture-flag bug) leaves its `scroll` listener
    // attached, so an unguarded `scroll` dispatch would throw inside that leaked listener — and
    // `dispatchEvent` doesn't propagate listener exceptions, so it can't be caught. Guard on a
    // real `__resizeTriggers__.firstElementChild` instead.
    const ready = (el: HTMLElement | null): el is HTMLElement =>
      !!el &&
      !!(el as unknown as { __resizeTriggers__?: HTMLElement }).__resizeTriggers__
        ?.firstElementChild;

    const dispatch = () => {
      // Re-resolve each time: NVL may have been recreated after mount.
      const cur = nvlRef.current?.getContainer?.() ?? null;
      if (ready(cur)) {
        try {
          cur.dispatchEvent(new Event("scroll"));
        } catch {
          /* best-effort */
        }
      }
    };

    const attach = (el: HTMLElement) => {
      if (observed === el) return;
      ro?.disconnect();
      observed = el;
      ro = new ResizeObserver(dispatch);
      ro.observe(el);
    };

    // Re-attach whenever NVL swaps in a new container (it replaces the element, leaving the
    // previous one detached, so the prior observer would go silent).
    const mo = new MutationObserver(() => {
      if (disposed) return;
      const el = nvlRef.current?.getContainer?.() ?? null;
      if (ready(el) && el !== observed) attach(el);
    });
    mo.observe(wrapperRef.current, { childList: true, subtree: true });

    // NVL is created in a child effect; retry briefly until its polyfill is attached.
    const tick = () => {
      if (disposed) return;
      const el = nvlRef.current?.getContainer?.() ?? null;
      if (ready(el)) attach(el);
      else if (++attempts < 120) raf = requestAnimationFrame(tick);
    };
    tick();

    return () => {
      disposed = true;
      cancelAnimationFrame(raf);
      ro?.disconnect();
      mo.disconnect();
    };
  }, []);

  const [neoNodes, neoRelationships] = useMemo(
    () => [transformNodes(nodes ?? []), transformRelationships(relationships ?? [])],
    [nodes, relationships],
  );

  const nvlOptionsWithoutWorkers = useMemo(
    () => ({
      ...nvlOptions,
      minZoom: 0,
      maxZoom: 1000,
      disableWebWorkers: true,
    }),
    [nvlOptions],
  );
  const [isSidePanelOpen, setIsSidePanelOpen] = useState(false);
  const [sidePanelWidth, setSidePanelWidth] = useState(300);

  // The legend is a floating overlay toggled by its own island button, independent of the side
  // panel (which holds the results overview / selection details). Show it automatically whenever a
  // legend becomes available so it is discoverable without a click. Runs only when the `legend`
  // trait changes, so it won't fight a user who has closed it.
  const [isLegendOpen, setIsLegendOpen] = useState(false);
  useEffect(() => {
    if (hasLegendContent(legend ?? EMPTY_LEGEND)) {
      setIsLegendOpen(true);
    }
  }, [legend]);
  const legendAvailable = hasLegendContent(legend ?? EMPTY_LEGEND);

  return (
    <NeedleThemeProvider theme={resolvedTheme} wrapperProps={{ isWrappingChildren: false }}>
      <div
        ref={wrapperRef}
        style={{
          position: "relative",
          height: height ?? "600px",
          width: width ?? "100%",
        }}
      >
        <GraphVisualization
          nodes={neoNodes}
          rels={neoRelationships}
          gesture={gesture}
          setGesture={setGesture}
          selected={selected ?? EMPTY_SELECTION}
          setSelected={setSelected}
          mouseEventCallbacks={{
            onNodeDoubleClick: (node) =>
              setLastDoubleClick({ kind: "node", id: String(node.id) }),
            onRelationshipDoubleClick: (rel) =>
              setLastDoubleClick({ kind: "relationship", id: String(rel.id) }),
          }}
          layout={layout}
          setLayout={setLayout}
          nvlOptions={nvlOptionsWithoutWorkers}
          nvlRef={nvlRef}
          zoom={zoom}
          pan={pan}
          layoutOptions={layoutOptions}
          sidepanel={{
            isSidePanelOpen,
            setIsSidePanelOpen,
            onSidePanelResize: setSidePanelWidth,
            sidePanelWidth,
            children: <GraphVisualization.SingleSelectionSidePanelContents />,
          }}
          topLeftIsland={<GraphVisualization.DownloadButton tooltipPlacement="right" />}
          topRightIsland={
            <IconButtonArray size="small" orientation="horizontal">
              {legendAvailable && (
                <IconButton
                  size="small"
                  isFloating
                  isActive={isLegendOpen}
                  description={isLegendOpen ? "Hide legend" : "Show legend"}
                  onClick={() => setIsLegendOpen((open) => !open)}
                  htmlAttributes={{ "aria-label": "Toggle legend" }}
                  tooltipProps={{ root: { placement: "bottom", isPortaled: false } }}
                >
                  <SwatchIconOutline />
                </IconButton>
              )}
              <GraphVisualization.ToggleSidePanelButton tooltipPlacement="bottom" />
            </IconButtonArray>
          }
          bottomRightIsland={
            <IconButtonArray size="medium" orientation="horizontal">
              <GraphVisualization.GestureSelectButton
                menuPlacement="top-end-bottom-end"
                tooltipPlacement="top"
              />
              <Divider orientation="vertical" />
              <GraphVisualization.ZoomInButton tooltipPlacement="top" />
              <GraphVisualization.ZoomOutButton tooltipPlacement="top" />
              <GraphVisualization.ZoomToFitButton tooltipPlacement="top" />
              {showLayoutButton && (
                <>
                  <Divider orientation="vertical" />
                  <GraphVisualization.LayoutSelectButton
                    menuPlacement="top-end-bottom-end"
                    tooltipPlacement="top"
                  />
                </>
              )}
            </IconButtonArray>
          }
        />
        {isLegendOpen && <Legend legend={legend ?? EMPTY_LEGEND} />}
      </div>
    </NeedleThemeProvider>
  );
}

function GraphWidgetWithErrorBoundary() {
  return (
    <GraphErrorBoundary>
      <GraphWidget />
    </GraphErrorBoundary>
  );
}

const render = createRender(GraphWidgetWithErrorBoundary);

export default { render };
