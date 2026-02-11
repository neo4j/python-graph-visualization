# Changes in 1.2.0

## Breaking changes

- Removed the `show_hover_tooltip` parameter from `render()` and `to_html()`. Tooltips are now always shown.
- `color_nodes()` and `color_relationships()` now default to `override=False`, meaning existing colors are preserved unless you explicitly pass `override=True`.

## New features

- New `render_widget()` method on `VisualizationGraph` returns a `GraphWidget` (anywidget) for interactive two-way data sync in Jupyter environments (JupyterLab, Notebook 7, VS Code, Colab).
- New `to_html()` method on `VisualizationGraph` as a convenience alias for `render()`.
- New `set_node_captions()` method for setting node captions based on a field or property.
- New `color_relationships()` method for coloring relationships by field or property (discrete or continuous).
- New `resize_relationships()` method for resizing relationship widths.
- New `width` field on `Relationship` model.
- `from_neo4j()` now accepts a `neo4j.Driver` directly, executing a default query internally.
- `from_dfs()` now accepts `rel_dfs=None` for node-only graphs.
- New `from_snowflake()` integration for importing data from Snowflake tables.
- Integration functions (`from_gds`, `from_neo4j`, `from_gql_create`, `from_snowflake`) now automatically set captions based on labels/type. Nodes are auto-colored by their caption in the JavaScript visualization.

## Bug fixes

## Improvements

- Migrated JavaScript visualization from `@neo4j-nvl/base` to `@neo4j-ndl/react-graph` React component.
- Migrated build system from Webpack to Vite.
- Added anywidget integration as the primary rendering path for Jupyter environments.
- Node and Relationship models now validate on assignment (`validate_assignment=True`).

## Deprecations

- `from_gds()`: `size_property`, `additional_node_properties`, and `node_radius_min_max` parameters are deprecated. Use `node_properties` and `resize_nodes()` on the returned `VisualizationGraph` instead.
- `from_neo4j()`: `size_property`, `node_caption`, `relationship_caption`, and `node_radius_min_max` parameters are deprecated. Use `set_node_captions()` and `resize_nodes()` on the returned `VisualizationGraph` instead.

## Other changes
