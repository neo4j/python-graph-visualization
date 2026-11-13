# Changes

## Breaking changes

## New features

* `GraphWidget` stores a static PNG snapshot of the graph next to the widget output, so a committed notebook
  still shows the graph on frontends that cannot render widgets, such as GitHub and nbviewer. The snapshot is
  taken once the initial layout has settled and refreshed after changes; live frontends keep the interactive
  widget. Disable it per widget with `render_widget(fallback=False)`.

## Bug fixes

## Improvements

## Other changes
