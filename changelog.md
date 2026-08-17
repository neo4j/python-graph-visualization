# Changes

## Breaking changes

## New features

## Bug fixes

* Fixed clicks being misaligned while the built-in "Node details" side panel is open ([#417](https://github.com/neo4j/python-graph-visualization/issues/417)). NVL sizes its canvas once at mount and did not recompute it when the side panel (`type: "push"`) flex-shrinks the graph container, so clicks were hit-tested against a stale, wider canvas and landed offset by the panel width. The widget now bridges a `ResizeObserver` to NVL's resize detection so the canvas tracks the container on panel open/close/animation/drag-resize. This is a temporary wrapper shim; the root cause (NVL not resizing its canvas on container changes, plus a leaked scroll-listener on destroy) is tracked for an upstream `@neo4j-nvl/base` fix — see `issue417_upstream_summary.md`.
* Fixed a stored cross-site scripting (XSS) vulnerability in `VG.render()`. Graph data was injected into an executable `<script>` block, so a node caption or property value containing `</script>` could break out and run arbitrary code in the browser of anyone opening a saved visualization. Data is now delivered as an inert `<script type="application/json">` block and read back with `JSON.parse`, with `<` escaped so no `</script>` can appear literally. The `render_widget` was unaffected.
* Fixed `widget.remove_data` leaving dangling relationships when only nodes were removed.
* Fixed `widget.remove_data` silently doing nothing when the id type differed (e.g. `Node(id=1)` vs `remove_data(nodes="1")`).
* Fixed `VisualizationGraph.resize_nodes` and `color_nodes` crashing with `ValueError: min() iterable argument is empty` when no node has the requested property. They now raise a `ValueError` that names the missing property.
* Fixed `VisualizationGraph.color_nodes` with `color_space=ColorSpace.CONTINUOUS` raising an unhelpful `TypeError` when colouring non-numeric (text) values. It now raises a `ValueError` suggesting `ColorSpace.DISCRETE`.
* Fixed the `max_allowed_nodes` limit only being enforced at draw time. `GraphWidget.add_data` now rejects additions that would exceed the limit set when the widget was created (via `render_widget`/`from_graph_data`), so the graph can no longer be grown past it afterwards.

## Improvements

## Other changes
