# Changes

## Breaking changes

## New features

* Nodes can display an icon, and nodes and relationships can display an overlay icon (for example a
  corner badge). Icons are set by name from a built-in catalog (`neo4j_viz.Icons`) or by URL, and local
  or remote images can be inlined with `neo4j_viz.icon_from_file`, `neo4j_viz.icon_from_url`, or a whole
  directory with `neo4j_viz.icons_from_directory`.

## Bug fixes

* Multiple `VG.render()` calls on one page (e.g. several notebook cells) no longer all display the first graph.
* `GraphWidget.save()` no longer times out intermittently when it is called right after the
  widget is displayed: the request now waits for the frontend to finish rendering instead of
  racing it.

## Improvements

## Other changes
