# Changes

## Breaking changes

## New features

* Added a color legend overlay to the visualization. It is captured automatically from `color_nodes`/`color_relationships`, can be set explicitly via `set_legend`, and toggled via `show_legend`.
* Added `neo4j_viz.streamlit.display_widget` to embed an interactive `GraphWidget` in a Streamlit app with two-way state sync (selection and options flow back to Python), following the Streamlit light/dark theme. Install with the `streamlit` extra (`pip install neo4j-viz[streamlit]`).

## Bug fixes

* Fixed a bug where nodes and relationships could not be selected on using `VG.render()`.

## Improvements

## Other changes
