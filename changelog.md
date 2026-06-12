# Changes in 1.5.0

## Breaking changes

## New features

* Add `GraphWidget` methods to change render options in place without re-rendering: `set_layout`, `set_zoom`, `set_pan`, `set_renderer`, and `set_show_layout_button`
* Add `GraphWidget` methods to change styling in place without re-rendering such as `color_relationships`

## Bug fixes

* Warn when relationships reference node ids that are not in the graph. It is configurable via the `on_dangling` parameter (`"warn"` (default), `"error"`, or `"none"`) on `render`, `render_widget`, and `GraphWidget.add_data`

## Improvements

* Support Python 3.14
* Support Aura Graph Analytics
* Support `gds.v2` endpoints
* Use typed options field in `GraphWidget`

## Other changes
