import { createRender, useModelState } from "@anywidget/react";
import "@neo4j-ndl/base/lib/neo4j-ds-styles.css";
import { GraphVisualization } from "@neo4j-ndl/react-graph";
import type { Layout, NvlOptions } from "@neo4j-nvl/base";
import { useMemo } from "react";
import {
  SerializedNode,
  SerializedRelationship,
  transformNodes,
  transformRelationships,
} from "./data-transforms";
import { GraphErrorBoundary } from "./graph-error-boundary";

type GraphOptions = {
  layout?: Layout;
  nvlOptions?: Partial<NvlOptions>;
  zoom?: number;
  pan?: { x: number; y: number };
  layoutOptions?: Record<string, unknown>;
};

function GraphWidget() {
  const [nodes] = useModelState<SerializedNode[]>("nodes");
  const [relationships] =
    useModelState<SerializedRelationship[]>("relationships");
  const [options] = useModelState<GraphOptions>("options");
  const [height] = useModelState<string>("height");
  const [width] = useModelState<string>("width");

  const { layout, nvlOptions, zoom, pan, layoutOptions } = options ?? {};
  const [neoNodes, neoRelationships] = useMemo(
    () => [
      transformNodes(nodes ?? []),
      transformRelationships(relationships ?? []),
    ],
    [nodes, relationships],
  );

  return (
    <div style={{ height: height ?? "600px", width: width ?? "100%" }}>
      <GraphVisualization
        nodes={neoNodes}
        rels={neoRelationships}
        layout={layout}
        nvlOptions={nvlOptions}
        zoom={zoom}
        pan={pan}
        layoutOptions={layoutOptions}
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
