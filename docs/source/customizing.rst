Customizing the visualization
=============================

Once created, a :doc:`VisualizationGraph object <./api-reference/visualization-graph>` can be modified in various ways
to adjust what the visualization looks like the next time you render it.
In this section we will discuss how to color, size, and pin nodes, as well as how to directly modify nodes and
relationships of existing ``VisualizationGraph`` objects.

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


Setting node captions
---------------------

Node captions are the text labels displayed on nodes in the visualization.

The ``set_node_captions`` method
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By calling the :meth:`neo4j_viz.VisualizationGraph.set_node_captions` method, you can set node captions based on a
node field (like ``id``, ``size``, etc.) or a node property (members of the ``Node.properties`` map).

The method accepts an ``override`` parameter (default ``True``) that controls whether to replace existing captions.
If ``override=False``, only nodes without captions will be updated.

Here's an example of setting node captions from a property:

.. code-block:: python

    # VG is a VisualizationGraph object with nodes that have a "name" property
    VG.set_node_captions(property="name")

You can also set captions from a node field, and choose not to override existing captions:

.. code-block:: python

    # VG is a VisualizationGraph object
    VG.set_node_captions(field="id", override=False)

For more complex scenarios where you need fallback logic or want to combine multiple properties, you can iterate over
nodes directly:

.. code-block:: python

    # VG is a VisualizationGraph object
    for node in VG.nodes:
        caption = node.properties.get("name") or node.properties.get("title") or node.id
        node.caption = str(caption)


Coloring nodes
--------------

Nodes can be colored directly by providing them with a color field, upon creation.
This can for example be done by passing a color as a string to the ``color`` parameter of the
:doc:`Node <./api-reference/node>` object.

Alternatively, you can color nodes based on a field or property of the nodes after a ``VisualizationGraph`` object has been
created.


The ``color_nodes`` method
~~~~~~~~~~~~~~~~~~~~~~~~~~

By calling the :meth:`neo4j_viz.VisualizationGraph.color_nodes` method, you can color nodes based on a
node field or property (members of the `Node.properties` map).

It's possible to color the nodes based on a discrete or continuous color space (see :doc:`ColorSpace <./api-reference/colors>`).
In the discrete case, a new color from the `colors` provided is assigned to each unique value of the node field/property.
In the continuous case, the `colors` should be a list of colors representing a range that are used to
create a gradient of colors based on the values of the node field/property.

By default the Neo4j color palette, that works for both light and dark mode, will be used.
If you want to use a different color palette, you can pass a dictionary or iterable of colors as the ``colors``
parameter.
A color value can for example be either strings like "blue", or hexadecimal color codes like "#FF0000", or even a tuple of RGB values like (255, 0, 255).

If some nodes already have a ``color`` set, you can choose whether or not to override it with the ``override``
parameter.


By discrete color space
***********************

To not use the default colors, we can provide a list of custom colors based on the discrete node field "caption" to the ``color_nodes`` method:

.. code-block:: python

    from neo4j_viz.colors import ColorSpace

    # VG is a VisualizationGraph object
    VG.color_nodes(
        field="caption",
        ["red", "#7fffd4", (255, 255, 255, 0.5), "hsl(270, 60%, 70%)"],
        color_space=ColorSpace.DISCRETE
    )

The full set of allowed values for colors are listed `here <https://docs.pydantic.dev/2.0/usage/types/extra_types/color_types/>`_.

Instead of defining your own colors, you could also for example use the color palettes from the `palettable library <https://jiffyclub.github.io/palettable/>`_ as in
this snippet:

.. code-block:: python

    from palettable.wesanderson import Moonrise1_5

    # VG is a VisualizationGraph object
    VG.color_nodes(field="caption", Moonrise1_5.colors)  # PropertyType.DISCRETE is default

In theses cases, all nodes with the same caption will get the same color.

If there are fewer colors than unique values for the node ``field`` or ``property`` provided, the colors will be reused in a cycle.
To avoid that, you could use a larger palette or extend one with additional colors. Please refer to the
:doc:`Visualizing Neo4j Graph Data Science (GDS) Graphs tutorial <./tutorials/gds-example>` for an example on how
to do the latter.


By continuous color space
*************************

To not use the default colors, we can provide a list of custom colors representing a range to the ``color_nodes`` method:

.. code-block:: python

    from neo4j_viz.colors import PropertyType

    # VG is a VisualizationGraph object
    VG.color_nodes(
        property="centrality_score",
        [(255, 0, 0), (191, 64, 0), (128, 128, 0), (64, 191, 0), (0, 255, 0)]  # From red to green
        color_space=ColorSpace.CONTINUOUS
    )

In this case, the nodes will be colored based on the value of the "centrality_score" property, with the lowest values being colored red and the highest values being colored green.
Since we only provided five colors in the range, the granularity of the gradient will be limited to five steps.

`palettable` and `matplotlib` are great libraries to use to create custom color gradients.


Sizing nodes
------------

Nodes can be given a size directly by providing them with a size field, upon creation.
This can for example be done by passing a size as an integer to the ``size`` parameter of the
:doc:`Node <./api-reference/node>` object.

Alternatively, you can size nodes after a ``VisualizationGraph`` object has been created.


The ``resize_nodes`` method
~~~~~~~~~~~~~~~~~~~~~~~~~~~

By calling the :meth:`neo4j_viz.VisualizationGraph.resize_nodes` method, you can resize nodes by:

* passing new nodes sizes as a dictionary ``sizes``, mapping node IDs to sizes in pixels, or
* providing a tuple of two numbers ``node_radius_min_max``: minimum and maximum radii (sizes) in pixels to which the
  nodes will be scaled.

Or you could provide both ``sizes`` and ``node_radius_min_max``, in which case the dictionary will be used to first set
the sizes of the nodes, and then the minimum and maximum values of the tuple will be subsequently used to scale the
sizes to the provided range.

If you provide only the ``node_radius_min_max`` parameter, the sizes of the nodes will be scaled such that the smallest
node will have the size of the first value, and the largest node will have the size of the second value.
The other nodes will be scaled linearly between these two values according to their relative size.
This can be useful if node sizes vary a lot, or are all very small or very big.

In the following example, we resize the node with ID 42 to have a size of 88 pixels, and then scales all nodes to have
sizes between 5 and 20 pixels:

.. code-block:: python

    # VG is a VisualizationGraph object
    VG.resize_nodes(sizes={42: 88}, node_radius_min_max=(5, 20))

Please note that means that also the node with ID 42 will be scaled to be between 5 and 20 pixels in size.


Pinning nodes
-------------

Nodes can be pinned to their current position in the visualization, so that they will not be moved by the force-directed
layout algorithm.
This can be useful if you want to keep a node in a specific position, for example to highlight it.

Nodes can be pinned directly upon creation.
This can for example be done by passing ``pinned=True`` to the :doc:`Node <./api-reference/node>` object.

Alternatively, you can toggle node pinning after a ``VisualizationGraph`` object has been created.


The ``toggle_nodes_pinned`` method
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By calling the :meth:`neo4j_viz.VisualizationGraph.toggle_nodes_pinned` method, you can toggle whether nodes should be
pinned or not.
This method takes dictionary that maps node IDs to boolean values, where ``True`` means that the node is pinned, and
``False`` means that the node is not pinned.

In the following example, we pin the node with ID 1337 and unpin the node with ID 42:

.. code-block:: python

    # VG is a VisualizationGraph object
    VG.toggle_nodes_pinned(1337: True, 42: False)})


Direct modification of nodes and relationships
----------------------------------------------

Nodes and relationships can also be modified directly by accessing the ``nodes`` and ``relationships`` fields of an
existing ``VisualizationGraph`` object.
These fields list of all the :doc:`Nodes <./api-reference/node>` and
:doc:`Relationships <./api-reference/relationship>` in the graph, respectively.

Each node and relationship has fields that can be accessed and modified directly, as in the following example:

.. code-block:: python

    # VG is a VisualizationGraph object

    # Modify the first node and fifth relationship
    VG.nodes[0].size = 10
    VG.nodes[0].properties["height"] = 170
    VG.relationships[4].caption = "BUYS"

    # Set the coordinates for all nodes from an existing property
    for node in VG.nodes:
        node.x = node.properties.get("x")
        node.y = node.properties.get("y")

    # Change the caption size for all relationships
    for relationship in VG.relationships:
        relationship.caption_size = 15


Any changes made to the nodes and relationships will be reflected in the next rendering of the graph.
