# Changes in 0.5.1

## Breaking changes

- Do not automatically derive size and caption for `from_neo4j`. Use the `size_property` and `node_caption` parameters to configure them.

## New features

## Bug fixes

- fixed a bug in `from_neo4j`, where the node size would always be set to the `size` property.
- fixed a bug in `from_neo4j`, where the node caption would always be set to the `caption` property.

## Improvements

## Other changes
