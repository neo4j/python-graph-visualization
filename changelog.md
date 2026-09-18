# Changes

## Breaking changes

## New features

- Add `GraphWidget.save()` to save the current visualization as a PNG or SVG file from a notebook cell (`await widget.save("graph.svg")`). The format is inferred from the file extension and defaults to SVG; a PNG captures the current view, an SVG the entire graph. Requires the widget to be displayed in a live notebook frontend.
- Add a search toolbar button that highlights matching nodes and relationships, in both the widget and static HTML exports. Toggle it via `show_search_button` on `render()`/`render_widget()` or `widget.set_show_search_button()` (on by default).
- Show the layout selector button in static HTML exports too, toggleable via `show_layout_button` on `render()`/`render_widget()` (on by default).

## Bug fixes

## Improvements

## Other changes
