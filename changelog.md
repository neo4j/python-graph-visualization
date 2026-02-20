# Changes in 1.2.0

## Breaking changes

- Removed the `show_hover_tooltip` parameter from `render()`. The visualization now shows a detail side panel for selected nodes and relationships, replacing the previous hover tooltip.
- Nodes are colored by default by their caption. Use `VG.color_nodes(field="caption", colors=[neo4j_viz.colors.NEO4J_COLORS_DISCRETE[0]])` to apply the previous coloring.


## New features

- Nodes are now automatically colored by their caption (label) in the JavaScript visualization. This works out of the box without needing to call `color_nodes()`, and applies regardless of how the graph was created. Explicit colors set via `color_nodes()` or directly on nodes take precedence. There is no longer a limit on the number of unique labels for auto-coloring.
- New `render_widget()` method on `VisualizationGraph` returns a `GraphWidget` (anywidget) for interactive two-way data sync in Jupyter environments (JupyterLab, Notebook 7, VS Code, Colab).

## Bug fixes

## Improvements

- Migrated JavaScript visualization from `@neo4j-nvl/base` to `@neo4j-ndl/react-graph` React component.
- Migrated build system from Webpack to Vite.
- Added anywidget integration as the primary rendering path for Jupyter environments.

## Other changes
