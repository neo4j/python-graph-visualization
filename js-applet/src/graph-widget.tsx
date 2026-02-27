import {createRender, useModelState} from "@anywidget/react";
import "@neo4j-ndl/base/lib/neo4j-ds-styles.css";
import {Gesture, GraphVisualization} from "@neo4j-ndl/react-graph";
import type {Layout, NvlOptions} from "@neo4j-nvl/base";
import {useEffect, useMemo, useState} from "react";
import {
    SerializedNode,
    SerializedRelationship,
    transformNodes,
    transformRelationships,
} from "./data-transforms";
import {GraphErrorBoundary} from "./graph-error-boundary";
import {Divider, IconButtonArray} from "@neo4j-ndl/react";

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
    if (document.body.classList.contains("vscode-light")) {
        return "light";
    }
    if (document.body.classList.contains("vscode-dark")) {
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
    const [options, setOptions] = useModelState<WidgetData["options"]>("options");
    const [height] = useModelState<WidgetData["height"]>("height");
    const [width] = useModelState<WidgetData["width"]>("width");
    const [theme] = useModelState<WidgetData["theme"]>("theme");
    const [gesture, setGesture] = useState<Gesture>('box');
    const {layout, nvlOptions, zoom, pan, layoutOptions, showLayoutButton} = options ?? {};
    const setLayout = (layout: Layout) => {
        setOptions({...options, layout});
    }

    useTheme(theme ?? "auto");

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
        <div style={{height: height ?? "600px", width: width ?? "100%"}}>
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
                sidepanel={{
                    isSidePanelOpen,
                    setIsSidePanelOpen,
                    onSidePanelResize: setSidePanelWidth,
                    sidePanelWidth,
                    children: <GraphVisualization.SingleSelectionSidePanelContents/>,
                }}
                topRightIsland={
                    <IconButtonArray size="medium">
                        <GraphVisualization.DownloadButton/>
                        <GraphVisualization.ToggleSidePanelButton/>
                    </IconButtonArray>
                }
                bottomRightIsland={
                    <IconButtonArray size="medium" orientation="vertical">
                        <GraphVisualization.GestureSelectButton menuPlacement="top-end-bottom-end"/>
                        <Divider orientation="vertical"/>
                        <GraphVisualization.ZoomInButton/>
                        <GraphVisualization.ZoomOutButton/>
                        <GraphVisualization.ZoomToFitButton/>
                        {showLayoutButton && (
                            <>
                                <Divider orientation="vertical"/>
                                <GraphVisualization.LayoutSelectButton menuPlacement="top-end-bottom-end"/>
                            </>
                        )}
                    </IconButtonArray>
                }
            />
        </div>
    );
}

function GraphWidgetWithErrorBoundary() {
    return (
        <GraphErrorBoundary>
            <GraphWidget/>
        </GraphErrorBoundary>
    );
}

const render = createRender(GraphWidgetWithErrorBoundary);

export default {render};
