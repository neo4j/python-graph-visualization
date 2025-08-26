.. Graph Visualization for Python by Neo4j documentation master file, created by
   sphinx-quickstart on Fri Jan 10 13:54:11 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Graph Visualization for Python by Neo4j documentation
=====================================================

This is the documentation for the ``neo4j-viz`` Python library by Neo4j.
The library allows you to visualize graph data interactively in Python using a simple API.

The library wraps the `Neo4j Visualization JavaScript library (NVL) <https://neo4j.com/docs/nvl/current/>`_, and
provides additional features for working with graph data in Python.
Notably, there are convenience methods for importing data from source such as `Pandas DataFrames <https://pandas.pydata.org/>`_,
`Neo4j Graph Data Science <https://neo4j.com/docs/graph-data-science/current/>`_, `Neo4j Database <https://neo4j.com/docs/python-manual/current/>`_
and `Snowflake tables <https://docs.snowflake.com/>`_.

The source code is available on `GitHub <https://github.com/neo4j/python-graph-visualization>`_.
If you have a suggestion on how we can improve the library or want to report a problem, you can create a `new issue <https://github.com/neo4j/python-graph-visualization/issues/new>`_.


.. toctree::
   :glob:
   :maxdepth: 1

   installation.rst
   getting-started.nblink
   integration.rst
   rendering.rst
   customizing.rst
   api-reference/index.rst
   tutorials/index.rst
