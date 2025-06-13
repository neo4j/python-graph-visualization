Rendering a graph
=================

In this section, we will discuss how to render a :doc:`VisualizationGraph object <./api-reference/visualization-graph>`
to display the graph visualization.

If you have not yet created a ``VisualizationGraph`` object, please refer to one of the following sections:

* :doc:`Getting started <./getting-started>` for creating a visualization graph from scratch using ``neo4j-viz``
  primitives like :doc:`Node <./api-reference/node>` and :doc:`Relationship <./api-reference/relationship>` and
  :doc:`VisualizationGraph <./api-reference/visualization-graph>` directly. Or
* :doc:`Integration with other libraries <./integration>` for importing data from a Pandas DataFrame or Neo4j GDS
  projection.

.. contents:: On this page:
   :depth: 1
   :local:
   :backlinks: none


The ``render`` method
---------------------

Once you have a ``VisualizationGraph`` object, you can render it using the ``render`` method.
This will return a HTML object that will be displayed in an environment that supports HTML rendering, such as
Jupyter notebooks or streamlit application.

All parameter of the ``render`` method are optional, and the full list of parameters of them is listed in the API
reference: :meth:`neo4j_viz.VisualizationGraph.render`.

The most important parameters to be aware of are the ``width`` and ``height`` parameters, which control the size of
HTML object that will be rendered.
You can provide these either as a percentage of the available space (eg. ``"80%"``), or as an absolute pixel value
(eg. ``"800px"``).

Further you can change the layout of the graph using the ``layout`` parameter, which can be set to one of the following values:

* ``Layout.FORCE_DIRECTED`` - Nodes are arranged using the Force-Directed algorithm, which simulates physical forces. To customize the layout, use `ForceDirectedOptions` via `layout_options`.`
* ``Layout.HIERARCHICAL`` - Arranges nodes by the directionality of their relationships, creating a tree-like structure.  To customize the layout use `HierarchicalLayoutOptions` via `layout_options`.`
* ``Layout.COORDINATE`` - Arranges nodes based on coordinates defined in `x` and `y` properties on each node.

Another thing of note is the ``max_allowed_nodes`` parameter, which controls the maximum number of nodes that is allowed
for the graph to contain in order to be rendered.
It defaults to 10.000, because rendering a large number of nodes can be slow and unresponsive.
However, you can increase this value if you are confident that your environment can handle the scale.
In this case you might also want to pass ``Renderer.WEB_GL`` as the ``renderer`` to improve performance.

By default a tooltip showing IDs and properties will be shown when mouse hovering over a node or relationship.
But you can disable this by passing ``show_hover_tooltip=False``.


Examples
~~~~~~~~

Please refer to the :doc:`Getting started section <./getting-started>` and the :doc:`tutorials <./tutorials/index>` for
examples of ``render`` method usage.


Exporting to HTML
~~~~~~~~~~~~~~~~~

The object returned by the ``render`` method is a ``IPython.display.HTML`` object.
In addition to being displayed in a Jupyter notebook or streamlit application, it can also be saved as an HTML file.
This could be useful if you want to share the visualization with others or embed it in a web page.

To save the HTML data to a file, you can use the ``data`` attribute of the HTML object:

.. code-block:: python

    html = VG.render(...)
    with open("my_graph.html", "w") as f:
        f.write(html.data)
