import datetime
from typing import Any

import pytest

from neo4j_viz import GraphWidget, Node, Relationship, VisualizationGraph
from neo4j_viz.options import Layout, RenderOptions
from neo4j_viz.widget import _serialize_entity


class TestSerializeEntity:
    def test_serialize_node(self) -> None:
        node = Node(id="n1", caption="Person", color="#ff0000")
        result = _serialize_entity(node)

        assert result["id"] == "n1"
        assert result["caption"] == "Person"
        assert result["color"] == "#ff0000"

    def test_serialize_relationship(self) -> None:
        rel = Relationship(source="n1", target="n2", caption="KNOWS")
        result = _serialize_entity(rel)

        assert result["from"] == "n1"
        assert result["to"] == "n2"
        assert result["caption"] == "KNOWS"

    def test_serialize_non_json_serializable_property(self) -> None:
        now = datetime.datetime.now()
        node = Node(
            id="n1",
            properties={"timestamp": now, "name": "test"},
        )
        result = _serialize_entity(node)

        # Non-serializable datetime should be converted to string
        assert result["properties"]["timestamp"] == str(now)
        # Regular properties should be unchanged
        assert result["properties"]["name"] == "test"

    def test_serialize_multiple_non_json_serializable_properties(self) -> None:
        now = datetime.datetime.now()
        custom_obj = object()
        node = Node(
            id="n1",
            properties={
                "timestamp": now,
                "custom": custom_obj,
                "normal": 123,
            },
        )
        result = _serialize_entity(node)

        assert result["properties"]["timestamp"] == str(now)
        assert result["properties"]["custom"] == str(custom_obj)
        assert result["properties"]["normal"] == 123


class TestGraphWidget:
    def test_from_graph_data_basic(self) -> None:
        nodes = [Node(id="n1", caption="A"), Node(id="n2", caption="B")]
        rels = [Relationship(source="n1", target="n2", caption="LINKS")]

        widget = GraphWidget.from_graph_data(nodes, rels)

        assert len(widget.nodes) == 2
        assert len(widget.relationships) == 1
        assert widget.width == "100%"
        assert widget.height == "600px"
        assert widget.options == {}

    def test_from_graph_data_with_options(self) -> None:
        nodes = [Node(id="n1")]
        rels: list[Relationship] = []

        widget = GraphWidget.from_graph_data(
            nodes,
            rels,
            width="800px",
            height="400px",
            options=RenderOptions(layout=Layout.FORCE_DIRECTED),
        )

        assert widget.width == "800px"
        assert widget.height == "400px"
        assert widget.options == {"layout": "d3Force", "showLayoutButton": False}

    def test_widget_trait_defaults(self) -> None:
        widget = GraphWidget()

        assert widget.nodes == []
        assert widget.relationships == []
        assert widget.width == "100%"
        assert widget.height == "600px"
        assert widget.options == {}


class TestWidgetDataBinding:
    """Test traitlet data binding - modifications that would sync to JS."""

    def test_update_nodes(self) -> None:
        widget = GraphWidget(nodes=[{"id": "n1", "caption": "A"}])
        assert len(widget.nodes) == 1

        # Simulate adding a node (as JS or Python might do)
        widget.nodes = [*widget.nodes, {"id": "n2", "caption": "B"}]
        assert len(widget.nodes) == 2
        assert widget.nodes[1]["id"] == "n2"

    def test_update_relationships(self) -> None:
        widget = GraphWidget(
            nodes=[{"id": "n1"}, {"id": "n2"}],
            relationships=[],
        )
        assert len(widget.relationships) == 0

        widget.relationships = [{"from": "n1", "to": "n2", "caption": "LINKS"}]
        assert len(widget.relationships) == 1

    def test_update_options(self) -> None:
        widget = GraphWidget(options={"layout": "d3Force"})

        widget.options = {"layout": "hierarchical", "zoom": 2.0}
        assert widget.options["layout"] == "hierarchical"
        assert widget.options["zoom"] == 2.0

    def test_update_dimensions(self) -> None:
        widget = GraphWidget()

        widget.width = "500px"
        widget.height = "300px"

        assert widget.width == "500px"
        assert widget.height == "300px"

    def test_observe_node_changes(self) -> None:
        """Test that traitlet observers fire on changes."""
        widget = GraphWidget()
        changes: list[dict[str, Any]] = []

        def on_change(change: dict[str, Any]) -> None:
            changes.append(change)

        widget.observe(on_change, names=["nodes"])

        widget.nodes = [{"id": "n1"}]

        assert len(changes) == 1
        assert changes[0]["name"] == "nodes"
        assert changes[0]["new"] == [{"id": "n1"}]

    def test_observe_multiple_traits(self) -> None:
        """Test observing multiple trait changes."""
        widget = GraphWidget()
        change_log: list[str] = []

        def log_change(change: dict[str, Any]) -> None:
            change_log.append(change["name"])

        widget.observe(log_change, names=["nodes", "relationships", "options"])

        widget.nodes = [{"id": "n1"}]
        widget.relationships = [{"from": "n1", "to": "n1"}]
        widget.options = {"zoom": 1.5}

        assert change_log == ["nodes", "relationships", "options"]

    def test_replace_all_data(self) -> None:
        """Test replacing entire graph data."""
        nodes = [Node(id="n1"), Node(id="n2")]
        rels = [Relationship(source="n1", target="n2")]
        widget = GraphWidget.from_graph_data(nodes, rels)

        # Replace with completely new data
        new_nodes = [Node(id="x1"), Node(id="x2"), Node(id="x3")]
        new_rels = [Relationship(source="x1", target="x2"), Relationship(source="x2", target="x3")]

        widget.nodes = [_serialize_entity(n) for n in new_nodes]
        widget.relationships = [_serialize_entity(r) for r in new_rels]

        assert len(widget.nodes) == 3
        assert len(widget.relationships) == 2
        assert widget.nodes[0]["id"] == "x1"

    def test_add_data(self) -> None:
        """Test adding new data to existing graph."""
        nodes = [Node(id="n1"), Node(id="n2")]
        rels = [Relationship(source="n1", target="n2")]
        widget = GraphWidget.from_graph_data(nodes, rels)

        widget.add_data(Node(id="x1"), Relationship(source="x1", target="x2"))

        assert len(widget.nodes) == 3
        assert len(widget.relationships) == 2

    def test_remove_data(self) -> None:
        """Test removing data from the graph."""
        node_1 = Node(id="n1")
        nodes = [node_1, Node(id="n2"), Node(id="n3")]
        rels = [
            Relationship(source="n1", target="n2"),
            Relationship(id=42, source="n2", target="n1"),
            Relationship(source="n2", target="n1"),  # detach delete
            Relationship(id=43, source="n3", target="n3"),
        ]
        widget = GraphWidget.from_graph_data(nodes, rels)

        widget.remove_data(nodes=[node_1, "n2"], relationships=[rels[0], "42"])
        assert {n["id"] for n in widget.nodes} == {"n3"}
        assert {r["id"] for r in widget.relationships} == {"43"}


render_widget_cases = {
    "default": {},
    "force layout": {"layout": Layout.FORCE_DIRECTED},
    "grid layout": {"layout": Layout.GRID},
    "coordinate layout": {"layout": Layout.COORDINATE},
    "hierarchical layout + options": {"layout": Layout.HIERARCHICAL, "layout_options": {"direction": "left"}},
    "with layout options": {"layout_options": {"gravity": 0.1}},
}


class TestRenderWidget:
    @pytest.mark.parametrize("render_option", render_widget_cases.values(), ids=render_widget_cases.keys())
    def test_basic_render_widget(self, render_option: dict[str, Any]) -> None:
        nodes = [
            Node(id="n1", caption="Person", x=1, y=10),
            Node(id="n2", caption="Product", x=2, y=15),
        ]
        relationships = [
            Relationship(source="n1", target="n2", caption="BUYS"),
        ]

        VG = VisualizationGraph(nodes=nodes, relationships=relationships)
        widget = VG.render_widget(**render_option)

        assert isinstance(widget, GraphWidget)
        assert len(widget.nodes) == 2
        assert len(widget.relationships) == 1

    def test_render_widget_max_allowed_nodes_limit(self) -> None:
        nodes = [Node(id=i) for i in range(10_001)]
        VG = VisualizationGraph(nodes=nodes, relationships=[])

        with pytest.raises(
            ValueError,
            match="Too many nodes .* to render",
        ):
            VG.render_widget(max_allowed_nodes=10_000)

    def test_render_widget_custom_dimensions(self) -> None:
        nodes = [Node(id="n1")]
        VG = VisualizationGraph(nodes=nodes, relationships=[])

        widget = VG.render_widget(width="800px", height="400px")

        assert widget.width == "800px"
        assert widget.height == "400px"

    def test_render_widget_with_non_json_serializable(self) -> None:
        now = datetime.datetime.now()
        node = Node(id="n1", properties={"timestamp": now})
        VG = VisualizationGraph(nodes=[node], relationships=[])

        # Should not raise
        widget = VG.render_widget()
        assert widget.nodes[0]["properties"]["timestamp"] == str(now)

    def test_render_widget_options_passed_through(self) -> None:
        nodes = [Node(id="n1")]
        VG = VisualizationGraph(nodes=nodes, relationships=[])

        widget = VG.render_widget(
            layout=Layout.HIERARCHICAL,
            initial_zoom=2.0,
            min_zoom=0.1,
            max_zoom=5.0,
        )

        assert widget.options["layout"] == "hierarchical"
        assert widget.options["zoom"] == 2.0
        assert widget.options["nvlOptions"]["minZoom"] == 0.1
        assert widget.options["nvlOptions"]["maxZoom"] == 5.0
