# Changes in 0.6.0

## Breaking changes

* Removed `table` property from nodes and relationships returned from `from_snowflake`, the table is represented by the `caption` field.
* Changed default value of `override` parameter in `VisualizationGraph.color_nodes()` from `False` to `True`. The method now overrides existing node colors by default. To preserve existing colors, explicitly pass `override=False`.

## New features


## Bug fixes

## Improvements


## Other changes
