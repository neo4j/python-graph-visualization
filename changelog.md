# Changes in 1.3.0

## Breaking changes

## New features

- Add convenience method `add_data` and `remove_data` to `GraphWidget`.
- Added a selection button to the toolbar.
- Added a layout button to the toolbar if `VG.render_widget` is used.
- Support the new circular layout.

## Bug fixes

- Fixed a bug with the theme detection inn VSCode.

## Improvements

- Allow setting the theme manually in `VG.render(theme="light")` and `VG.render_widget(theme="dark")`.
- Use typed nodes and relationship traitlets in GraphWidget, i.e., list of Node and Relationship instead of dictionaries.
- `render` now allows to pass `layout` as a string as well. Previously expected to be a typed `neo4j_viz.Layout`. 
- Fixed rendering in Marimo notebooks


## Other changes
