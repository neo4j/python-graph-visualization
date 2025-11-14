# Changes in 0.6.0

## Breaking changes

- Removed `table` property from nodes and relationships returned from `from_snowflake`, the table is represented by the `caption` field.
- Changed default value of `override` parameter in `VisualizationGraph.color_nodes()` from `False` to `True`. The method now overrides existing node colors by default. To preserve existing colors, explicitly pass `override=False`.

## New features

- Added `set_node_captions()` convenience method to `VisualizationGraph` for setting node captions from a field or property.

## Bug fixes

## Improvements

- Truncate large property values in the rendered output.

## Other changes
