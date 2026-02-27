# type: ignore

import marimo

__generated_with = "0.20.2"
app = marimo.App(width="full", app_title="Neo4jVizExample")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Neo4j Graph Visualization with Marimo

    This example demonstrates how to use `neo4j-viz` to visualize graphs in Marimo notebooks.
    We'll create a simple graph representing a social network with people and their relationships.
    """)
    return


@app.cell
def _():
    from neo4j_viz import Node, Relationship, VisualizationGraph

    return Node, Relationship, VisualizationGraph


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Create Nodes and Relationships
    """)
    return


@app.cell
def _(Node, Relationship):
    # Create nodes representing people
    nodes = [
        Node(id=0, size=10, caption="Person", properties={"age": 25}),
        Node(id=1, size=10, caption="Product", properties={"price": 100}),
        Node(id=2, size=20, caption="Product", properties={"price": 200}),
        Node(id=3, size=10, caption="Person", properties={"age": 30}),
        Node(id=4, size=10, caption="Product"),
    ]
    relationships = [
        Relationship(source=0, target=1, caption="BUYS"),
        Relationship(source=0, target=2, caption="BUYS"),
        Relationship(source=3, target=2, caption="BUYS"),
    ]
    return nodes, relationships


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Visualize the Graph as a Widget
    """)
    return


@app.cell
def _(VisualizationGraph, nodes, relationships):
    # Create and render the visualization
    VG = VisualizationGraph(nodes=nodes, relationships=relationships)
    widget = VG.render_widget(theme="light", renderer="canvas")
    widget
    return VG, widget


@app.cell
def _(widget):
    print(widget.theme)
    print(widget.options)
    return


@app.cell
def _(Node, Relationship, widget):
    # Run this cell multiple times - each run adds a new node to the widget above
    import random

    new_id = len(widget.nodes)
    target_id = random.choice([n["id"] for n in widget.nodes])

    new_node = Node(id=new_id, size=10, caption="Person")
    new_rel = Relationship(source=new_id, target=target_id, caption="KNOWS")

    widget.add_data(nodes=[new_node], relationships=[new_rel])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Standalone Visualization the Graph
    """)
    return


@app.cell
def _(VG):
    import os

    VG.render()
    return


if __name__ == "__main__":
    app.run()
