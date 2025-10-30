# Changes in 0.6.0

## Breaking changes

- Change API of integrations to only provide basic parameters. Any further configuration should happen ons the Visualization Graph object:
  - Don't derive fields from properties. Use utility functions on the VisualizationGraph instead or set them manually on the node/relationship objects (VG.nodes/VG.relationships). This affects `from_neo4j`, `from_gds`, `from_gql_create`, `from_pandas`, `from_snowflake`.
  - `from_gds` rename `additional_node_properties` to `node_properties`
  - Drop parameters `size_property`, `node_radius_min_max`. Use `VG.resize_nodes(property=...)` instead. This affects `from_gds`, `from_neo4j`, `from_pandas`, `from_gql_create`, `from_snowflake`.

## New features

- Allow to include db node properties in addition to the properties in the GDS Graph. Specify `db_node_properties` in `from_gds`.

## Bug fixes

- Color nodes in `from_snowflake` only if there are less than 13 node tables used. This avoids reuse of colors for different tables.
- fixed a bug in `from_gds`, where properties of type list could not be imported.

## Improvements

- Validate fields of a node and relationship not only at construction but also on assignment.
- Allow resizing per node property such as `VG.resize_nodes(property="score")`.
- Color nodes by label in `from_gds` and `from_gql_create`.
- Add `table` property to nodes and relationships created by `from_snowflake`. This is used as a default caption.

## Other changes
