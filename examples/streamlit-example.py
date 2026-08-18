import pathlib
import random

import streamlit as st
from neo4j_viz import Node, Relationship, VisualizationGraph
from neo4j_viz.streamlit import display_widget

# Path to this file
script_path = pathlib.Path(__file__).resolve()


st.title("Neo4j Viz Streamlit Example")
st.text("This is an example of how to use Streamlit with the Graph Visualization for Python library by Neo4j.")


def create_small_graph() -> VisualizationGraph:
    people = [
        ("Alice", "Engineer"),
        ("Bob", "Designer"),
        ("Carol", "Engineer"),
        ("Dan", "Manager"),
    ]
    nodes = [Node(id=str(i), caption=name, properties={"role": role}) for i, (name, role) in enumerate(people)]
    relationships = [
        Relationship(source="0", target="1", caption="KNOWS"),
        Relationship(source="1", target="2", caption="KNOWS"),
        Relationship(source="2", target="3", caption="KNOWS"),
    ]
    vg = VisualizationGraph(nodes=nodes, relationships=relationships)
    # Coloring by a property populates the legend overlay shown in the widget.
    vg.color_nodes(property="role")
    return vg


small_graph = create_small_graph()

# Nodes/relationships added at runtime, kept in session state so they survive reruns.
if "added_nodes" not in st.session_state:
    st.session_state.added_nodes = []
    st.session_state.added_relationships = []

with st.sidebar:
    height = st.slider("Height in pixels", 100, 2000, 600, 50)
    if st.button("Add random node"):
        existing_ids = [n.id for n in small_graph.nodes] + [n.id for n in st.session_state.added_nodes]
        new_node = Node(id=f"added-{len(st.session_state.added_nodes)}", caption="New", size=20)
        st.session_state.added_nodes.append(new_node)
        # Link the new node to a random existing one.
        st.session_state.added_relationships.append(
            Relationship(
                source=new_node.id,
                target=random.choice(existing_ids),
                caption="LINKS_TO",
            )
        )
    show_code = st.checkbox("Show code")

st.header("Interactive widget")
st.text(
    "A small graph rendered as an interactive widget, colored by role (see the "
    "legend overlay). Selecting nodes or relationships in the graph syncs the "
    "selection back to Python, and Python can push data changes back to the graph "
    "— use the sidebar button to watch a new node appear and link into the graph."
)

# Build the widget from the small graph plus any runtime additions.
graph_widget = small_graph.render_widget(height=f"{height}px")
if st.session_state.added_nodes:
    graph_widget.add_data(st.session_state.added_nodes, st.session_state.added_relationships)

display_widget(graph_widget, key="small-graph-widget")

selection = graph_widget.selected
st.write(f"Selected {len(selection.nodeIds)} node(s) and {len(selection.relationshipIds)} relationship(s).")
if selection.nodeIds:
    st.write("Selected node IDs:", selection.nodeIds)

if show_code:
    st.header("Code")
    st.code(script_path.read_text())
