import datetime
import re
from typing import Any

import pytest

from neo4j_viz import GraphSelection, GraphWidget, Node, Relationship, VisualizationGraph
from neo4j_viz.options import DoubleClickEvent, Layout, Renderer, RenderOptions, SelectionMode, WidgetOptions
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
        assert widget.options == WidgetOptions()

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
        assert widget.options == WidgetOptions(layout="d3Force", show_layout_button=False)

    def test_widget_trait_defaults(self) -> None:
        widget = GraphWidget()

        assert widget.nodes == []
        assert widget.relationships == []
        assert widget.width == "100%"
        assert widget.height == "600px"
        assert widget.options == WidgetOptions()


class TestWidgetDataBinding:
    """Test traitlet data binding - modifications that would sync to JS."""

    def test_update_nodes(self) -> None:
        widget = GraphWidget(nodes=[Node(id="n1", caption="A")])
        assert len(widget.nodes) == 1

        # Simulate adding a node (as JS or Python might do)
        widget.nodes = [*widget.nodes, Node(id="n2", caption="B")]
        assert len(widget.nodes) == 2
        assert widget.nodes[1].id == "n2"

    def test_update_relationships(self) -> None:
        widget = GraphWidget(
            nodes=[Node(id="n1"), Node(id="n2")],
            relationships=[],
        )
        assert len(widget.relationships) == 0

        widget.relationships = [Relationship(source="n1", target="n2", caption="LINKS")]
        assert len(widget.relationships) == 1
        assert widget.relationships[0].source == "n1"
        assert widget.relationships[0].target == "n2"

    def test_update_options(self) -> None:
        widget = GraphWidget(options={"layout": "d3Force"})

        new_options: Any = {"layout": "hierarchical", "zoom": 2.0}
        widget.options = new_options
        assert widget.options == WidgetOptions(layout="hierarchical", zoom=2.0)

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

        widget.nodes = [Node(id="n1")]

        assert len(changes) == 1
        assert changes[0]["name"] == "nodes"
        assert len(changes[0]["new"]) == 1
        assert changes[0]["new"][0].id == "n1"

    def test_observe_multiple_traits(self) -> None:
        """Test observing multiple trait changes."""
        widget = GraphWidget()
        change_log: list[str] = []

        def log_change(change: dict[str, Any]) -> None:
            change_log.append(change["name"])

        widget.observe(log_change, names=["nodes", "relationships", "options"])

        widget.nodes = [Node(id="n1")]
        widget.relationships = [Relationship(source="n1", target="n1")]
        widget.options = WidgetOptions(zoom=1.5)

        assert change_log == ["nodes", "relationships", "options"]

    def test_replace_all_data(self) -> None:
        """Test replacing entire graph data."""
        nodes = [Node(id="n1"), Node(id="n2")]
        rels = [Relationship(source="n1", target="n2")]
        widget = GraphWidget.from_graph_data(nodes, rels)

        # Replace with completely new data
        new_nodes = [Node(id="x1"), Node(id="x2"), Node(id="x3")]
        new_rels = [Relationship(source="x1", target="x2"), Relationship(source="x2", target="x3")]

        widget.nodes = new_nodes
        widget.relationships = new_rels

        assert len(widget.nodes) == 3
        assert len(widget.relationships) == 2
        assert widget.nodes[0].id == "x1"

    def test_add_data(self) -> None:
        """Test adding new data to existing graph."""
        nodes = [Node(id="n1"), Node(id="n2")]
        rels = [Relationship(source="n1", target="n2")]
        widget = GraphWidget.from_graph_data(nodes, rels)

        widget.add_data([Node(id="x1"), Node(id="x2")], Relationship(source="x1", target="x2"))

        assert len(widget.nodes) == 4
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
        assert {n.id for n in widget.nodes} == {"n3"}
        assert {r.id for r in widget.relationships} == {43}

    def test_remove_data_nodes_only_deletes_dangling_relationships(self) -> None:
        nodes = [Node(id="n1"), Node(id="n2")]
        rels = [
            Relationship(source="n1", target="n2"),
            Relationship(source="n2", target="n2"),
        ]
        widget = GraphWidget.from_graph_data(nodes, rels)

        widget.remove_data(nodes=["n1"])
        assert {n.id for n in widget.nodes} == {"n2"}
        # The relationship that pointed at the removed node is deleted, not left dangling.
        assert {(r.source, r.target) for r in widget.relationships} == {("n2", "n2")}

    def test_remove_data_relationships_only(self) -> None:
        nodes = [Node(id="n1"), Node(id="n2")]
        rels = [Relationship(id="r1", source="n1", target="n2"), Relationship(id="r2", source="n2", target="n1")]
        widget = GraphWidget.from_graph_data(nodes, rels)

        widget.remove_data(relationships=["r1"])
        assert {n.id for n in widget.nodes} == {"n1", "n2"}
        assert {r.id for r in widget.relationships} == {"r2"}

    def test_remove_data_id_type_mismatch(self) -> None:
        widget = GraphWidget.from_graph_data([Node(id=1), Node(id=2)], [Relationship(source=1, target=2)])

        widget.remove_data(nodes="1")
        assert {n.id for n in widget.nodes} == {2}
        # Relationship pointing at the removed node is also deleted.
        assert widget.relationships == []

    def test_add_data_exceeds_max_allowed_nodes(self) -> None:
        widget = GraphWidget.from_graph_data([Node(id="n1")], [], max_allowed_nodes=10)

        with pytest.raises(ValueError, match="exceeds the maximum of 10 nodes"):
            widget.add_data(nodes=[Node(id=f"x{i}") for i in range(10)])

        # The graph must be left unchanged when the limit would be exceeded.
        assert {n.id for n in widget.nodes} == {"n1"}

    def test_add_data_max_allowed_nodes_threaded_from_render_widget(self) -> None:
        """A custom max_allowed_nodes passed to render_widget is honored by add_data (L-03)."""
        vg = VisualizationGraph(nodes=[Node(id="n1")], relationships=[])
        widget = vg.render_widget(max_allowed_nodes=3)

        # Up to the limit is fine.
        widget.add_data(nodes=[Node(id="n2")])
        assert len(widget.nodes) == 2

        with pytest.raises(ValueError, match="exceeds the maximum of 3 nodes"):
            widget.add_data(nodes=[Node(id=f"x{i}") for i in range(3)])

    def test_add_data_dangling_warns_by_default(self) -> None:
        widget = GraphWidget.from_graph_data([Node(id="n1")], [])
        with pytest.warns(UserWarning, match=re.escape("reference node ids that are not in the graph")):
            widget.add_data(relationships=Relationship(source="n1", target="missing"))

    def test_add_data_dangling_error(self) -> None:
        widget = GraphWidget.from_graph_data([Node(id="n1")], [])
        with pytest.raises(ValueError, match=re.escape("reference node ids that are not in the graph")):
            widget.add_data(relationships=Relationship(source="n1", target="missing"), on_dangling="error")

    def test_add_data_node_and_relationship_together_ok(self) -> None:
        widget = GraphWidget.from_graph_data([Node(id="n1")], [])
        # adding the endpoint node together with the relationship must not be flagged
        widget.add_data(Node(id="n2"), Relationship(source="n1", target="n2"))
        assert len(widget.relationships) == 1


class TestWidgetUtilityMethods:
    def _spy_send_state(self, widget: GraphWidget) -> list[Any]:
        synced: list[Any] = []
        widget.send_state = lambda key=None: synced.append(key)
        return synced

    def test_color_nodes(self) -> None:
        widget = GraphWidget(nodes=[Node(id="n1", properties={"label": "A"}), Node(id="n2", properties={"label": "B"})])
        synced = self._spy_send_state(widget)

        widget.color_nodes(property="label")

        assert widget.nodes[0].color is not None
        assert widget.nodes[1].color is not None
        assert widget.nodes[0].color != widget.nodes[1].color
        # Mutating in place must still push the updated nodes to the frontend, and coloring also
        # updates (and syncs) the captured legend.
        assert synced == ["legend", "nodes"]

    def test_color_relationships(self) -> None:
        widget = GraphWidget(
            nodes=[Node(id="n1"), Node(id="n2")],
            relationships=[
                Relationship(source="n1", target="n2", caption="KNOWS"),
                Relationship(source="n2", target="n1", caption="LIKES"),
            ],
        )
        synced = self._spy_send_state(widget)

        widget.color_relationships(field="caption")

        assert widget.relationships[0].color is not None
        assert widget.relationships[0].color != widget.relationships[1].color
        # Coloring also updates (and syncs) the captured legend.
        assert synced == ["legend", "relationships"]

    def test_resize_nodes(self) -> None:
        widget = GraphWidget(
            nodes=[
                Node(id="n1", properties={"score": 10}),
                Node(id="n2", properties={"score": 20}),
            ]
        )
        synced = self._spy_send_state(widget)

        widget.resize_nodes(property="score", node_radius_min_max=(10, 50))

        assert widget.nodes[0].size == 10
        assert widget.nodes[1].size == 50
        assert synced == ["nodes"]

    def test_resize_relationships(self) -> None:
        widget = GraphWidget(
            nodes=[Node(id="n1"), Node(id="n2")],
            relationships=[Relationship(id="r1", source="n1", target="n2")],
        )
        synced = self._spy_send_state(widget)

        widget.resize_relationships(widths={"r1": 5})

        assert widget.relationships[0].width == 5
        assert synced == ["relationships"]

    def test_set_node_captions(self) -> None:
        widget = GraphWidget(nodes=[Node(id="n1", properties={"name": "Alice"})])
        synced = self._spy_send_state(widget)

        widget.set_node_captions(property="name")

        assert widget.nodes[0].caption == "Alice"
        assert synced == ["nodes"]

    def test_toggle_nodes_pinned(self) -> None:
        widget = GraphWidget(nodes=[Node(id="n1", pinned=False), Node(id="n2")])
        synced = self._spy_send_state(widget)

        widget.toggle_nodes_pinned({"n1": True})

        assert widget.nodes[0].pinned is True
        assert widget.nodes[1].pinned is None
        assert synced == ["nodes"]


class TestWidgetSelection:
    def test_selection_defaults_to_empty(self) -> None:
        widget = GraphWidget(nodes=[Node(id="n1")])

        assert widget.selected == GraphSelection()
        assert widget.selected.nodeIds == []
        assert widget.selected.relationshipIds == []

    def test_selection_holds_selected_ids(self) -> None:
        widget = GraphWidget(
            nodes=[Node(id="n1"), Node(id="n2")],
            relationships=[Relationship(id="r1", source="n1", target="n2")],
        )

        widget.selected = GraphSelection(nodeIds=["n1"], relationshipIds=["r1"])

        assert widget.selected.nodeIds == ["n1"]
        assert widget.selected.relationshipIds == ["r1"]

    def test_selection_coerces_dict_from_frontend(self) -> None:
        """The frontend syncs a plain dict, which is coerced to a typed GraphSelection."""
        widget = GraphWidget(nodes=[Node(id="n1"), Node(id="n2")])

        widget.selected = GraphSelection(nodeIds=["n2"], relationshipIds=[])
        assert widget.selected.nodeIds == ["n2"]

    def test_selection_serializes_for_frontend(self) -> None:
        selection = GraphSelection(nodeIds=["n1"], relationshipIds=["r1"])

        assert selection.to_json() == {"nodeIds": ["n1"], "relationshipIds": ["r1"]}

    def test_selection_syncs_from_frontend(self) -> None:
        """The `selected` trait is two-way synced, so observers fire when the frontend updates it."""
        widget = GraphWidget(nodes=[Node(id="n1")])
        changes: list[dict[str, Any]] = []
        widget.observe(lambda change: changes.append(change), names=["selected"])

        widget.selected = GraphSelection(nodeIds=["n1"])

        assert len(changes) == 1
        assert changes[0]["name"] == "selected"

    def test_on_selection_change_receives_graph_selection(self) -> None:
        widget = GraphWidget(nodes=[Node(id="n1")])
        received: list[GraphSelection] = []
        widget.on_selection_change(received.append)

        widget.selected = GraphSelection(nodeIds=["n1"])

        assert len(received) == 1
        assert isinstance(received[0], GraphSelection)
        assert received[0].nodeIds == ["n1"]

    def test_on_selection_change_fires_on_dict_from_frontend(self) -> None:
        """A raw dict from the frontend is coerced before the callback sees it."""
        widget = GraphWidget(nodes=[Node(id="n1"), Node(id="n2")])
        received: list[GraphSelection] = []
        widget.on_selection_change(received.append)

        widget.selected = GraphSelection(nodeIds=["n2"], relationshipIds=[])

        assert len(received) == 1
        assert received[0].nodeIds == ["n2"]

    def test_on_selection_change_returns_handler_for_unobserve(self) -> None:
        widget = GraphWidget(nodes=[Node(id="n1")])
        received: list[GraphSelection] = []
        handler = widget.on_selection_change(received.append)

        widget.selected = GraphSelection(nodeIds=["n1"])
        assert len(received) == 1

        widget.unobserve(handler, names=["selected"])
        widget.selected = GraphSelection(relationshipIds=["r1"])
        assert len(received) == 1


class TestWidgetDoubleClick:
    def test_last_double_click_defaults_to_none(self) -> None:
        widget = GraphWidget(nodes=[Node(id="n1")])
        assert widget.last_double_click is None

    def test_double_click_syncs_from_frontend(self) -> None:
        """The `last_double_click` trait is synced, so observers fire when the frontend updates it."""
        widget = GraphWidget(nodes=[Node(id="n1")])
        changes: list[dict[str, Any]] = []
        widget.observe(lambda change: changes.append(change), names=["last_double_click"])

        widget.last_double_click = DoubleClickEvent(kind="node", id="n1")

        assert len(changes) == 1
        assert changes[0]["name"] == "last_double_click"

    def test_on_node_double_click_receives_resolved_node(self) -> None:
        widget = GraphWidget(nodes=[Node(id="n1", caption="A"), Node(id="n2")])
        received: list[Node | None] = []
        widget.on_node_double_click(received.append)

        widget.last_double_click = DoubleClickEvent(kind="node", id="n1")

        assert len(received) == 1
        assert isinstance(received[0], Node)
        assert received[0].id == "n1"

    def test_on_node_double_click_yields_none_for_unknown_id(self) -> None:
        widget = GraphWidget(nodes=[Node(id="n1")])
        received: list[Node | None] = []
        widget.on_node_double_click(received.append)

        widget.last_double_click = DoubleClickEvent(kind="node", id="gone")

        assert received == [None]

    def test_on_node_double_click_ignores_relationship_events(self) -> None:
        widget = GraphWidget(
            nodes=[Node(id="n1"), Node(id="n2")],
            relationships=[Relationship(id="r1", source="n1", target="n2")],
        )
        received: list[Node | None] = []
        widget.on_node_double_click(received.append)

        widget.last_double_click = DoubleClickEvent(kind="relationship", id="r1")

        assert received == []

    def test_on_relationship_double_click_receives_resolved_relationship(self) -> None:
        widget = GraphWidget(
            nodes=[Node(id="n1"), Node(id="n2")],
            relationships=[Relationship(id="r1", source="n1", target="n2", caption="REL")],
        )
        received: list[Relationship | None] = []
        widget.on_relationship_double_click(received.append)

        widget.last_double_click = DoubleClickEvent(kind="relationship", id="r1")

        assert len(received) == 1
        assert isinstance(received[0], Relationship)
        assert received[0].id == "r1"

    def test_on_relationship_double_click_ignores_node_events(self) -> None:
        widget = GraphWidget(nodes=[Node(id="n1")])
        received: list[Relationship | None] = []
        widget.on_relationship_double_click(received.append)

        widget.last_double_click = DoubleClickEvent(kind="node", id="n1")

        assert received == []

    def test_on_node_double_click_returns_handler_for_unobserve(self) -> None:
        widget = GraphWidget(nodes=[Node(id="n1"), Node(id="n2")])
        received: list[Node | None] = []
        handler = widget.on_node_double_click(received.append)

        widget.last_double_click = DoubleClickEvent(kind="node", id="n1")
        assert len(received) == 1

        widget.unobserve(handler, names=["last_double_click"])
        widget.last_double_click = DoubleClickEvent(kind="node", id="n2")
        assert len(received) == 1


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
        assert _serialize_entity(widget.nodes[0])["properties"]["timestamp"] == str(now)

    def test_render_widget_options_passed_through(self) -> None:
        nodes = [Node(id="n1")]
        VG = VisualizationGraph(nodes=nodes, relationships=[])

        widget = VG.render_widget(
            layout=Layout.HIERARCHICAL,
            initial_zoom=2.0,
            min_zoom=0.1,
            max_zoom=5.0,
        )

        assert widget.options.layout == "hierarchical"
        assert widget.options.zoom == 2.0
        assert widget.options.nvl_options is not None
        assert widget.options.nvl_options.min_zoom == 0.1
        assert widget.options.nvl_options.max_zoom == 5.0


class TestRenderOptionSetters:
    def test_set_layout(self) -> None:
        widget = GraphWidget()

        widget.set_layout(Layout.HIERARCHICAL)

        assert widget.options.layout == "hierarchical"

    def test_set_layout_with_options(self) -> None:
        widget = GraphWidget()

        widget.set_layout(Layout.FORCE_DIRECTED, {"gravity": 0.1})

        assert widget.options.layout == "d3Force"
        assert widget.options.layout_options == {"gravity": 0.1}

    def test_set_layout_clears_stale_layout_options(self) -> None:
        widget = GraphWidget(options={"layoutOptions": {"gravity": 0.1}})

        widget.set_layout(Layout.GRID)

        assert widget.options.layout == "grid"
        assert widget.options.layout_options is None

    def test_set_layout_with_mismatched_options_raises(self) -> None:
        widget = GraphWidget()

        with pytest.raises(ValueError):
            widget.set_layout(Layout.HIERARCHICAL, {"gravity": 0.1})

    def test_set_zoom(self) -> None:
        widget = GraphWidget()

        widget.set_zoom(2.0)

        assert widget.options.zoom == 2.0

    def test_set_pan(self) -> None:
        widget = GraphWidget()

        widget.set_pan(100, 50)
        assert widget.options.pan is not None
        assert widget.options.pan.x == 100
        assert widget.options.pan.y == 50

    def test_set_renderer_canvas(self) -> None:
        widget = GraphWidget()

        widget.set_renderer(Renderer.CANVAS)

        assert widget.options.nvl_options is not None
        assert widget.options.nvl_options.disable_web_gl is True

    def test_set_renderer_webgl(self) -> None:
        widget = GraphWidget()

        with pytest.warns(UserWarning):
            widget.set_renderer(Renderer.WEB_GL)

        assert widget.options.nvl_options is not None
        assert widget.options.nvl_options.disable_web_gl is False

    def test_set_renderer_preserves_other_nvl_options(self) -> None:
        widget = GraphWidget(options={"nvlOptions": {"minZoom": 0.1}})

        widget.set_renderer(Renderer.CANVAS)

        assert widget.options.nvl_options is not None
        assert widget.options.nvl_options.min_zoom == 0.1
        assert widget.options.nvl_options.disable_web_gl is True

    def test_set_show_layout_button(self) -> None:
        widget = GraphWidget()

        widget.set_show_layout_button()
        assert widget.options.show_layout_button is True

        widget.set_show_layout_button(False)
        assert widget.options.show_layout_button is False

    def test_set_selection_mode_enum(self) -> None:
        widget = GraphWidget()

        widget.set_selection_mode(SelectionMode.BOX)

        assert widget.options.selection_mode == SelectionMode.BOX

    def test_set_selection_mode_string(self) -> None:
        widget = GraphWidget()

        widget.set_selection_mode("lasso")

        assert widget.options.selection_mode == SelectionMode.LASSO

    def test_set_selection_mode_invalid_raises(self) -> None:
        widget = GraphWidget()

        with pytest.raises(ValueError):
            widget.set_selection_mode("nonsense")

    def test_setter_preserves_unrelated_options(self) -> None:
        widget = GraphWidget(options={"layout": "hierarchical"})

        widget.set_zoom(3.0)

        assert widget.options.zoom == 3.0
        assert widget.options.layout == "hierarchical"

    def test_setter_triggers_sync(self) -> None:
        widget = GraphWidget()
        changes: list[dict[str, Any]] = []
        widget.observe(lambda change: changes.append(change), names=["options"])

        widget.set_zoom(2.0)

        assert len(changes) == 1
        assert changes[0]["name"] == "options"
