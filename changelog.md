# Changes in 0.5.1

## Breaking changes

- Do not automatically derive size and caption for `from_neo4j` and `from_gql_create`. Use the `size_property` and `node_caption` parameters to explicitly configure them.
- Change API of integrations to only provide basic parameters. Any further configuration should happen ons the Visualization Graph object:
  - `from_pandas`
    - Drop `node_radius_min_max` parameter. `VG.resize_nodes(...)` instead
  - `from_neo4j`, `from_gds`, `from_gql_create`
    - Drop parameters `size_property`, `node_radius_min_max`. Use `VG.resize_nodes(property=...)` instead
    - rename additional_node_properties to node_properties
    - Don't derive fields from properties. Use `VG.map_properties_to_fields` instead

## New features

- Allow to include db node properties in addition to the properties in the GDS Graph. Specify `db_node_properties` in `from_gds`.

## Bug fixes

- fixed a bug in `from_neo4j`, where the node size would always be set to the `size` property.
- fixed a bug in `from_neo4j`, where the node caption would always be set to the `caption` property.
- Color nodes in `from_snowflake` only if there are less than 13 node tables used. This avoids reuse of colors for different tables.

## Improvements

- Validate fields of a node and relationship not only at construction but also on assignment.
- Allow resizing per node property such as `VG.resize_nodes(property="score")`.
- Color nodes by label in `from_gds` and `from_gql_create`.
- Add `table` property to nodes and relationships created by `from_snowflake`. This is used as a default caption.

## Other changes
