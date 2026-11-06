# Changes

## Breaking changes

## New features

* Nodes can display an icon, and nodes and relationships can display an overlay icon (for example a
  corner badge). Icons are set by name from a built-in catalog (`neo4j_viz.Icons`) or by URL, and local
  or remote images can be inlined with `neo4j_viz.icon_from_file`, `neo4j_viz.icon_from_url`, or a whole
  directory with `neo4j_viz.icons_from_directory`.
* The `Layout.GPU_FORCE` layout uses NVL's GPU-accelerated force simulation. It supports clustering of nodes by
  a node property, with an optional cluster outline or halo, via `ClusteringOptions` in
  `ForceDirectedLayoutOptions`. It requires `Renderer.WEB_GL`.
* The `Layout.HIERARCHICAL` layout supports clustering of nodes by a node property via the
  `HierarchicalLayoutOptions.clusterBy` option.
* The force-directed layout accepts a `seedingMethod` option (how initial node positions are seeded), and
  the `render`/`render_widget` methods accept `min_fps`/`max_fps` to cap the rendering frame rate.

## Bug fixes

* Multiple `VG.render()` calls on one page (e.g. several notebook cells) no longer all display the first graph.
* `GraphWidget.save()` no longer times out intermittently when it is called right after the
  widget is displayed: the request now waits for the frontend to finish rendering instead of
  racing it.

## Improvements

* Since NVL 2.0 the WebGL renderer renders node icons and relationship arrowheads, so the warning shown when
  selecting `Renderer.WEB_GL` now only mentions captions (which remain canvas-only).

## Other changes
