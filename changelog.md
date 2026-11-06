# Changes

## Breaking changes

## New features

* Nodes can display an icon, and nodes and relationships can display an overlay icon (for example a
  corner badge). Icons are set by name from a built-in catalog (`neo4j_viz.Icons`) or by URL, and local
  or remote images can be inlined with `neo4j_viz.icon_from_file`, `neo4j_viz.icon_from_url`, or a whole
  directory with `neo4j_viz.icons_from_directory`.
* The `Layout.GPU_FORCE` layout uses NVL's GPU-accelerated force simulation. It supports clustering of nodes by
  a node property, with an optional cluster outline or halo, via `ClusteringOptions` in
  `ForceDirectedLayoutOptions`. It works with any renderer.
* The `Layout.HIERARCHICAL` layout supports clustering of nodes by a node property via the
  `HierarchicalLayoutOptions.clusterBy` option.
* The GPU force layout accepts a `seedingMethod` option (how initial node positions are seeded), and
  the `render`/`render_widget` methods accept `min_fps`/`max_fps` to budget the layout steps run per
  frame while a layout is active (only noticeable on large graphs).

## Bug fixes

* Multiple `VG.render()` calls on one page (e.g. several notebook cells) no longer all display the first graph.
* `GraphWidget.save()` no longer times out intermittently when it is called right after the
  widget is displayed: the request now waits for the frontend to finish rendering instead of
  racing it.

## Improvements

* `Renderer.WEB_GL` now selects NVL's WebGL renderer (it previously only enabled the GPU context without changing
  how the graph was drawn). WebGL drawing is faster for large graphs but does not render captions; the warning is
  now only shown when the graph actually has captions that would be dropped.
* The wrapper warns when force-directed layout options (`gravity`, `simulationStopVelocity`, `seedingMethod`,
  `clustering`) are set on `Layout.FORCE_DIRECTED`, since NVL's d3-force layout ignores them; use `Layout.GPU_FORCE`.
* Since NVL 2.0 the WebGL renderer renders node icons and relationship arrowheads; only captions remain canvas-only.

## Other changes
