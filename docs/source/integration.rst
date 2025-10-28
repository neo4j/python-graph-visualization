Integration with other libraries
================================

In addition to creating graphs from scratch, with ``neo4j-viz`` as is shown in the
:doc:`Getting started section <./getting-started>`, you can also import data directly from external sources.
In this section we will cover how to import data from `Pandas DataFrames <https://pandas.pydata.org/>`_,
`Neo4j Graph Data Science <https://neo4j.com/docs/graph-data-science/current/>`_,
`Neo4j Database <https://neo4j.com/docs/python-manual/current/>`_,
`GQL CREATE queries <https://neo4j.com/docs/cypher-manual/current/clauses/create/>`_,
and `Snowflake tables <https://docs.snowflake.com/>`_.


.. contents:: On this page:
   :depth: 1
   :local:
   :backlinks: none


Pandas DataFrames
-----------------

The ``neo4j-viz`` library provides a convenience method for importing data from Pandas DataFrames.
These DataFrames can be created from many sources, such as CSV files.
It requires and additional dependency to be installed, which you can do by running:

.. code-block:: bash

    pip install neo4j-viz[pandas]

Once you have installed the additional dependency, you can use the :doc:`from_pandas <./api-reference/from_pandas>` method
to import pandas DataFrames.

The ``from_dfs`` method takes two mandatory positional parameters:

* A Pandas ``DataFrame``, or iterable (eg. list) of DataFrames representing the nodes of the graph.
  The rows of the DataFrame(s) should represent the individual nodes, and the columns should represent the node
  IDs and attributes.
  The node ID will be set on the :doc:`Node <./api-reference/node>`,
  Other columns will be a key in each node's `properties` dictionary, that maps to the node's corresponding
  value in the column.
  If the graph has no node properties, the nodes can be derived from the relationships DataFrame alone.
* A Pandas ``DataFrame``, or iterable (eg. list) of DataFrames representing the relationships of the graph.
  The rows of the DataFrame(s) should represent the individual relationships, and the columns should represent the
  relationship IDs and attributes.
  The relationship id, source and target node IDs will be set on the :doc:`Relationship <./api-reference/relationship>`.
  Other columns will be a key in each relationship's `properties` dictionary, that maps to the relationship's corresponding
  value in the column.


Example
~~~~~~~

In this small example, we import a tiny toy graph representing a social network from two Pandas DataFrames.
As we can see the column names of the DataFrames map directly to the fields of :doc:`Nodes <./api-reference/node>`
and :doc:`Relationships <./api-reference/relationship>`.

.. code-block:: python

    from pandas import DataFrame
    from neo4j_viz.pandas import from_dfs

    nodes = DataFrame({
        "id": [1, 2, 3],
        "caption": ["Alice", "Bob", "Charlie"],
        "size": [20, 10, 10],
    })
    relationships = DataFrame({
        "source": [1, 2],
        "target": [2, 3],
        "caption": ["LIKES", "KNOWS"],
    })

    VG = from_dfs(nodes, relationships)


Neo4j Graph Data Science (GDS) library
--------------------------------------

The ``neo4j-viz`` library provides a convenience method for importing data from the Neo4j Graph Data Science (GDS)
library.
It requires and additional dependency to be installed, which you can do by running:

.. code-block:: bash

    pip install neo4j-viz[gds]

Once you have installed the additional dependency, you can use the :doc:`from_gds <./api-reference/from_gds>` method
to import projections from the GDS library.

The ``from_gds`` method takes two mandatory positional parameters:

* An initialized ``GraphDataScience`` object for the connection to the GDS instance, and
* A ``Graph`` representing the projection that one wants to import.

The optional ``max_node_count`` parameter can be used to limit the number of nodes that are imported from the
projection.
By default, it is set to 10.000, meaning that if the projection has more than 10.000 nodes, ``from_gds`` will sample
from it using random walk with restarts, to get a smaller graph that can be visualized.
If you want to have more control of the sampling, such as choosing a specific start node for the sample, you can call
a `sampling <https://neo4j.com/docs/graph-data-science/current/management-ops/graph-creation/sampling/>`_
method yourself and passing the resulting projection to ``from_gds``.

The ``node_properties`` parameter is also optional, and should be a list of additional node properties of the
projection that you want to include in the visualization.
The default is ``None``, which means that all properties of the nodes in the projection will be included.
Apart from being visible through on-hover tooltips, these properties could be used to color the nodes, or give captions
to them in the visualization, or simply included in the nodes' ``Node.properties`` maps without directly impacting the
visualization.
If you want to include node properties stored at the Neo4j database, you can include them in the visualization by using the `db_node_properties` parameter.


Example
~~~~~~~

In this small example, we import a graph projection from the GDS library, that has the node properties "pagerank" and
"componentId".
We use the "pagerank" property to compute the size of the nodes, and the "componentId" property to color the nodes.

.. code-block:: python

    from graphdatascience import GraphDataScience
    from neo4j_viz.gds import from_gds

    gds = GraphDataScience(...)
    G = gds.graph.project(...)

    # Compute the PageRank and Weakly Connected Components
    gds.pageRank.mutate(G, mutateProperty="pagerank")
    gds.wcc.mutate(G, mutateProperty="componentId")

    # Import the projection into a `VisualizationGraph`
    # Make sure to include `pagerank` and `componentId`
    VG = from_gds(
        gds,
        G,
        node_properties=["componentId"],
    )
    # Size the nodes by the `pagerank` property
    VG.resize_nodes(property="pagerank")

    # Color the nodes by the `componentId` property, so that the nodes are
    # colored by the connected component they belong to
    VG.color_nodes(property="componentId")


Please see the :doc:`Visualizing Neo4j Graph Data Science (GDS) Graphs tutorial <./tutorials/gds-example>` for a
more extensive example.


Neo4j Database
--------------

The ``neo4j-viz`` library provides a convenience method for importing data from Neo4j.
It requires and additional dependency to be installed, which you can do by running:

.. code-block:: bash

    pip install neo4j-viz[neo4j]

Once you have installed the additional dependency, you can use the :doc:`from_neo4j <./api-reference/from_neo4j>` method
to import query results from Neo4j.

The ``from_neo4j`` method takes one mandatory positional parameter:
A ``data`` argument representing either a query result in the shape of a ``neo4j.graph.Graph`` or ``neo4j.Result``, or a
``neo4j.Driver`` in which case a simple default query will be executed internally to retrieve the graph data.

The optional ``max_rows`` parameter can be used to limit the number of relationships shown in the visualization.
By default, it is set to 10.000, meaning that if the database has more than 10.000 rows, a warning will be raised.
Note, this only applies if the ``data`` parameter is a ``neo4j.Driver``.


Example
~~~~~~~

In this small example, we import a graph from a Neo4j query result.

.. code-block:: python

    from neo4j import GraphDatabase, RoutingControl, Result
    from neo4j_viz.gds import from_gds

    # Modify this to match your Neo4j instance's URI and credentials
    URI = "neo4j://localhost:7687"
    auth = ("neo4j", "password")

    with GraphDatabase.driver(URI, auth=auth) as driver:
        driver.verify_connectivity()

        result = driver.execute_query(
            "MATCH (n)-[r]->(m) RETURN n,r,m",
            database_="neo4j",
            routing_=RoutingControl.READ,
            result_transformer_=Result.graph,
        )

    VG = from_neo4j(result)


Please see the :doc:`Visualizing Neo4j Graphs tutorial <./tutorials/neo4j-example>` for a
more extensive example.


GQL ``CREATE`` query
--------------------

The ``neo4j-viz`` library provides convenience for creating visualization graphs from GQL ``CREATE`` queries via the :doc:`from_gql_create <./api-reference/from_gql_create>` method.

The ``from_gql_create`` method takes one mandatory positional parameter:

* A valid ``query`` representing a GQL ``CREATE`` query as a string.


Example
~~~~~~~

In this small example, we create a visualization graph from a GQL ``CREATE`` query.

.. code-block:: python

    from neo4j_viz.gql_create import from_gql_create

    query = """
            CREATE
              (a:User {name: 'Alice', age: 23}),
              (b:User {name: 'Bridget', age: 34}),
              (c:User {name: 'Charles', age: 45}),
              (d:User {name: 'Dana', age: 56}),
              (e:User {name: 'Eve', age: 67}),
              (f:User {name: 'Fawad', age: 78}),

              (a)-[:LINK {weight: 0.5}]->(b),
              (a)-[:LINK {weight: 4}]->(c),
              (e)-[:LINK {weight: 1.1}]->(d),
              (e)-[:LINK {weight: -2}]->(f);
            """

    VG = from_gql_create(query)


Snowflake Tables
----------------

The ``neo4j-viz`` library provides a convenience method for importing data from Snowflake tables.
It requires and additional dependency to be installed, which you can do by running:

.. code-block:: bash

    pip install neo4j-viz[snowflake]

Once you have installed the additional dependency, you can use the :doc:`from_snowflake <./api-reference/from_snowflake>` method
to import Snowflake tables into a ``VisualizationGraph``.

The ``from_snowflake`` method takes two mandatory positional parameters:

* A ``snowflake.snowpark.Session`` object for the connection to Snowflake, and
* A `project configuration <https://neo4j.com/docs/snowflake-graph-analytics/current/jobs/#jobs-project>`_ as a dictionary, that specifies how you want your tables to be projected as a graph.
  This configuration is the same as the project configuration of the `Neo4j Snowflake Graph Analytics application <https://neo4j.com/docs/snowflake-graph-analytics/current/>`_.

You can further customize the visualization after the `VisualizationGraph` has been created, by using the methods described in the :doc:`Customizing the visualization <./customizing>` section.


Default behavior
~~~~~~~~~~~~~~~~

The node and relationship captions will be set to the names of the corresponding tables.
The nodes will be colored so that nodes from the same table have the same color, and different tables have different colors.


Example
~~~~~~~

In this small example, we import a toy graph representing a social network from two tables in Snowflake.

.. code-block:: python

    from snowflake.snowpark import Session
    from neo4j_viz.snowflake import from_dfs

    # Configure according to your own setup
    connection_parameters = {
        "account": os.environ.get("SNOWFLAKE_ACCOUNT"),
        "user": os.environ.get("SNOWFLAKE_USER"),
        "password": os.environ.get("SNOWFLAKE_PASSWORD"),
        "role": os.environ.get("SNOWFLAKE_ROLE"),
        "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE"),
    }

    session.sql(
        "CREATE OR REPLACE TABLE EXAMPLE_DB.DATA_SCHEMA.PERSONS (NODEID VARCHAR);"
    ).collect()

    session.sql("""
    INSERT INTO EXAMPLE_DB.DATA_SCHEMA.PERSONS VALUES
      ('Alice'),
      ('Bob'),
      ('Carol'),
      ('Dave'),
      ('Eve');
      """).collect()

    session.sql(
        "CREATE OR REPLACE TABLE EXAMPLE_DB.DATA_SCHEMA.KNOWS (SOURCENODEID VARCHAR, TARGETNODEID VARCHAR);"
    ).collect()

    session.sql("""
    INSERT INTO EXAMPLE_DB.DATA_SCHEMA.KNOWS VALUES
      ('Alice', 'Dave'),
      ('Alice', 'Carol'),
      ('Bob',   'Carol'),
      ('Dave',  'Eve'),
      """).collect()

    VG = from_snowflake(
        session,
        {
            "nodeTables": [
                "EXAMPLE_DB.DATA_SCHEMA.PERSONS",
            ],
            "relationshipTables": {
                "EXAMPLE_DB.DATA_SCHEMA.KNOWS": {
                    "sourceTable": "EXAMPLE_DB.DATA_SCHEMA.PERSONS",
                    "targetTable": "EXAMPLE_DB.DATA_SCHEMA.PERSONS",
                    "orientation": "UNDIRECTED",
                }
            },
        },
    )

For a full example of the ``from_snowflake`` importer in action, please see the
:doc:`Visualizing Snowflake Tables tutorial <./tutorials/snowflake-example>`.
