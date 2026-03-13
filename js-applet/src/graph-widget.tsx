import { createRender, useModelState } from "@anywidget/react";
import ndlCssText from "@neo4j-ndl/base/lib/neo4j-ds-styles.css?inline";
import { Gesture, GraphVisualization } from "@neo4j-ndl/react-graph";
import type { Layout, NvlOptions } from "@neo4j-nvl/base";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  SerializedNode,
  SerializedRelationship,
  transformNodes,
  transformRelationships,
} from "./data-transforms";
import { GraphErrorBoundary } from "./graph-error-boundary";
import {
  Divider,
  IconButtonArray,
  NeedleThemeProvider,
} from "@neo4j-ndl/react";

export type Theme = "dark" | "light" | "auto";

export type GraphOptions = {
  layout: Layout;
  nvlOptions?: Partial<NvlOptions>;
  zoom?: number;
  pan?: { x: number; y: number };
  layoutOptions?: Record<string, unknown>;
  showLayoutButton: boolean;
};

export type WidgetData = {
  nodes: SerializedNode[];
  relationships: SerializedRelationship[];
  options: GraphOptions;
  height: string;
  width: string;
  theme: Theme;
};

function detectTheme(): "light" | "dark" {
  if (document.body.classList.contains("vscode-light") || document.body.classList.contains("light-theme")) {
    return "light";
  }
  if (document.body.classList.contains("vscode-dark") || document.body.classList.contains("dark-theme")) {
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

// @font-face rules in shadow DOM adopted stylesheets don't register fonts at the
// document level, so the browser can't find them for rendering. We extract and hoist
// them into document.head eagerly at module load so fonts begin loading immediately.
const fontFaceRules = (ndlCssText.match(/@font-face\s*\{[^}]*\}/g) || []).join(
  "\n"
);
if (fontFaceRules) {
  const fontStyle = document.createElement("style");
  fontStyle.textContent = fontFaceRules;
  document.head.appendChild(fontStyle);
}

let cssInjected = false;

/**
 * Injects the full NDL stylesheet into the appropriate scope. In a shadow DOM
 * context (e.g. Marimo notebooks), the CSS is adopted onto the shadow root so
 * tokens, resets and component styles are properly scoped. Outside shadow DOM,
 * a regular <style> element is appended to document.head.
 */
function injectNdlCss(el: HTMLElement) {
  if (cssInjected) return;
  cssInjected = true;

  const rootNode = el.getRootNode();
  if (rootNode instanceof ShadowRoot) {
    const sheet = new CSSStyleSheet();
    sheet.replaceSync(ndlCssText);
    rootNode.adoptedStyleSheets = [...rootNode.adoptedStyleSheets, sheet];
  } else {
    const style = document.createElement("style");
    style.textContent = ndlCssText;
    document.head.appendChild(style);
  }
}

function GraphWidget() {
  const [nodes] = useModelState<WidgetData["nodes"]>("nodes");
  const [relationships] =
    useModelState<WidgetData["relationships"]>("relationships");
  const [options, setOptions] = useModelState<WidgetData["options"]>("options");
  const [height] = useModelState<WidgetData["height"]>("height");
  const [width] = useModelState<WidgetData["width"]>("width");
  const [theme] = useModelState<WidgetData["theme"]>("theme");
  const [gesture, setGesture] = useState<Gesture>("box");
  const { layout, nvlOptions, zoom, pan, layoutOptions, showLayoutButton } =
    options ?? {};
  const setLayout = (layout: Layout) => {
    setOptions({ ...options, layout });
  };

  const wrapperRef = useRef<HTMLDivElement>(null);
  const resolvedTheme = resolveTheme(theme ?? "auto");
  const [portalTarget, setPortalTarget] = useState<HTMLElement | null>(null);

  useEffect(() => {
    if (!wrapperRef.current) return;
    injectNdlCss(wrapperRef.current);

    if (wrapperRef.current.getRootNode() instanceof ShadowRoot) {
      setPortalTarget(wrapperRef.current);
    }
  }, []);

  const [neoNodes, neoRelationships] = useMemo(
    () => [
      transformNodes(nodes ?? []),
      transformRelationships(relationships ?? []),
    ],
    [nodes, relationships]
  );

  const nvlOptionsWithoutWorkers = useMemo(
    () => ({
      ...nvlOptions,
      minZoom: 0,
      maxZoom: 1000,
      disableWebWorkers: true,
    }),
    [nvlOptions]
  );
  const [isSidePanelOpen, setIsSidePanelOpen] = useState(false);
  const [sidePanelWidth, setSidePanelWidth] = useState(300);

  return (
    <NeedleThemeProvider
      theme={resolvedTheme}
      wrapperProps={{ isWrappingChildren: false }}
    >
      <div
        ref={wrapperRef}
        style={{ height: height ?? "600px", width: width ?? "100%" }}
      >
        <GraphVisualization
          nodes={neoNodes}
          rels={neoRelationships}
          gesture={gesture}
          setGesture={setGesture}
          layout={layout}
          setLayout={setLayout}
          nvlOptions={nvlOptionsWithoutWorkers}
          zoom={zoom}
          pan={pan}
          layoutOptions={layoutOptions}
          portalTarget={portalTarget}
          sidepanel={{
            isSidePanelOpen,
            setIsSidePanelOpen,
            onSidePanelResize: setSidePanelWidth,
            sidePanelWidth,
            children: <GraphVisualization.SingleSelectionSidePanelContents />,
          }}
          topLeftIsland={
            <GraphVisualization.DownloadButton tooltipPlacement="right" />
          }
          topRightIsland={
            <GraphVisualization.ToggleSidePanelButton tooltipPlacement="left" />
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
