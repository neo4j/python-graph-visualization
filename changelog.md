# Changes in 0.4.0


## Breaking changes

* The `from_gds` method now fetches all node properties of a given GDS projection by default, instead of none.
* The `from_gds` method now adds node labels as captions for nodes.
* The `from_gds` method now samples large graphs before fetching them by default, but this can be overridden.


## New features

* Allow visualization based only on relationship DataFrames, without specifying node DataFrames in `from_dfs`
* Add relationship properties to `VisualizationGraph` when constructing via `from_gds`
* Allow setting `layout_options` for `VisualizationGraph::render`


## Bug fixes


## Improvements

* Improved error messages when constructing `VisualizationGraph`s using `from_dfs`, `from_neo4j`, `from_gds` and `from_gql_create` methods


## Other changes
