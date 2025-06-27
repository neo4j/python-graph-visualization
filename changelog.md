# Changes in 0.4.1


## Breaking changes

* Relationship types are now added as the default caption on relationships when fetched using `from_gds`


## New features

* Allow passing a `neo4j.Driver` instance as input to `from_neo4j`, in which case the driver will be used internally to fetch the graph data using a simple query
* Added optional argument `dropna` to `from_dfs` loader allowing for not including NaN properties in the created visualization graph


## Bug fixes

* Make sure that temporary internal node properties are not included in the visualization output
* Fixed bug where loading a graph with `from_gds` where all node or relationship properties are not present on every entity would result in an error


## Improvements


## Other changes
