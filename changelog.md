# Changes in 0.5.1

## Breaking changes

- Do not automatically derive size and caption for `from_neo4j` and `from_gql_create`. Use the `size_property` and `node_caption` parameters to explicitly configure them.

## New features

## Bug fixes

- fixed a bug in `from_neo4j`, where the node size would always be set to the `size` property.
- fixed a bug in `from_neo4j`, where the node caption would always be set to the `caption` property.

## Improvements

- Validate fields of a node and relationship not only at construction but also on assignment.

## Other changes
