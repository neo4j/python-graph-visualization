# Changes

## Breaking changes

* `VisualizationGraph.resize_nodes` and `GraphWidget.resize_nodes` now scale the node sizes to the
  `node_radius_min_max` range by area instead of by radius, so that the node area grows linearly with the size.
  This matches how the Neo4j Bloom graph app sizes nodes, but it changes the node sizes of existing calls.
  Pass `sizing=NodeSizing.RADIUS` to keep the linear radius scaling of earlier versions.

## New features

* `VisualizationGraph.resize_nodes` and `GraphWidget.resize_nodes` take a `sizing` parameter
  (`NodeSizing.AREA`, `NodeSizing.RADIUS` or `NodeSizing.LOG`) to choose how the node sizes map to node radii.

* `GraphWidget` stores a static PNG snapshot of the graph next to the widget output, so a committed notebook
  still shows the graph on frontends that cannot render widgets, such as GitHub and nbviewer. The snapshot is
  taken once the initial layout has settled and refreshed after changes; live frontends keep the interactive
  widget. Disable it per widget with `render_widget(fallback=False)`.
* `render()` and `render_widget()` frame the whole graph once its initial layout has settled, for every
  layout. Pass `fit=False` to keep the default view instead. `GraphWidget.fit()` frames the graph again
  on demand, for example after changing the graph or the layout.

## Bug fixes

* An explicit `initial_zoom` or `pan_position` is no longer overridden once the layout settles. Previously
  only the force-directed and hierarchical layouts were framed automatically, and that framing also ignored
  the zoom and pan set from Python.

## Improvements

* Rendering with `Layout.COORDINATE` warns when nodes have no coordinates, since those nodes stack at the
  center of the canvas. The `Layout` docstrings now describe how each layout uses node coordinates.

## Other changes
