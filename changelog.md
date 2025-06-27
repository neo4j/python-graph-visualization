# Changes in 0.4.1


## Breaking changes

* Relationship types are now added as the default caption on relationships when fetched using `from_gds`


## New features

* Allow passing a `neo4j.Driver` instance as input to `from_neo4j`, in which case the driver will be used internally to fetch the graph data using a simple query


## Bug fixes

* Make sure that temporary internal node properties are not included in the visualization output.


## Improvements


## Other changes
