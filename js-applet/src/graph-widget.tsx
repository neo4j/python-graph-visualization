import { createRender, useModelState } from "@anywidget/react";
import "@neo4j-ndl/base/lib/neo4j-ds-styles.css";
import { GraphVisualization } from "@neo4j-ndl/react-graph";
import type { Layout, NvlOptions } from "@neo4j-nvl/base";
import { useEffect, useMemo, useState } from "react";
import {
  SerializedNode,
  SerializedRelationship,
  transformNodes,
  transformRelationships,
} from "./data-transforms";
import { GraphErrorBoundary } from "./graph-error-boundary";

export type Theme = "dark" | "light" | "auto";

export type GraphOptions = {
  layout?: Layout;
  nvlOptions?: Partial<NvlOptions>;
  zoom?: number;
  pan?: { x: number; y: number };
  layoutOptions?: Record<string, unknown>;
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
  return brightness < 128 ? "dark" : "light";
}

function useTheme(theme: Theme) {
  useEffect(() => {
    const resolved = theme === "auto" ? detectTheme() : theme;
    document.documentElement.className = `ndl-theme-${resolved}`;
  }, [theme]);
}

function GraphWidget() {
  const [nodes] = useModelState<WidgetData["nodes"]>("nodes");
  const [relationships] =
    useModelState<WidgetData["relationships"]>("relationships");
  const [options] = useModelState<WidgetData["options"]>("options");
  const [height] = useModelState<WidgetData["height"]>("height");
  const [width] = useModelState<WidgetData["width"]>("width");
  const [theme] = useModelState<WidgetData["theme"]>("theme");

  useTheme(theme ?? "auto");

  const { layout, nvlOptions, zoom, pan, layoutOptions } = options ?? {};
  const [neoNodes, neoRelationships] = useMemo(
    () => [
      transformNodes(nodes ?? []),
      transformRelationships(relationships ?? []),
    ],
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

  return (
    <div style={{ height: height ?? "600px", width: width ?? "100%" }}>
      <GraphVisualization
        nodes={neoNodes}
        rels={neoRelationships}
        layout={layout}
        nvlOptions={nvlOptionsWithoutWorkers}
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
      />
    </div>
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
