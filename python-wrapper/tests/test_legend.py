import json
from typing import Any

from pydantic_extra_types.color import Color

from neo4j_viz import GraphWidget, Legend, LegendEntry, LegendSection, Node, Relationship, VisualizationGraph
from neo4j_viz.colors import ColorSpace


def _hex(color: str) -> str:
    return Color(color).as_hex(format="long")


def test_default_legend_is_empty() -> None:
    VG = VisualizationGraph(nodes=[Node(id="0")], relationships=[])

    assert VG.legend == Legend()
    assert VG.legend.nodes is None
    assert VG.legend.relationships is None
    assert VG.legend.visible is True
    assert VG.legend.to_json() == {"visible": True}


def test_color_nodes_populates_discrete_legend() -> None:
    nodes = [
        Node(id="0", properties={"label": "Movie"}),
        Node(id="1", properties={"label": "Director"}),
        Node(id="2", properties={"label": "Movie"}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.color_nodes(property="label", colors=["#000000", "#00FF00"])

    section = VG.legend.nodes
    assert section is not None
    assert section.title == "label"
    assert section.color_space == ColorSpace.DISCRETE
    assert section.entries == [
        LegendEntry(label="Movie", color=_hex("#000000")),
        LegendEntry(label="Director", color=_hex("#00FF00")),
    ]
    # Legend colors match the colors actually applied to the nodes.
    assert VG.nodes[0].color == Color(section.entries[0].color)
    assert VG.nodes[1].color == Color(section.entries[1].color)


def test_color_nodes_continuous_legend_is_gradient() -> None:
    nodes = [
        Node(id="0", properties={"score": 10}),
        Node(id="1", properties={"score": 20}),
        Node(id="2", properties={"score": 30}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.color_nodes(property="score", color_space=ColorSpace.CONTINUOUS, colors=["#000000", "#FFFFFF"])

    section = VG.legend.nodes
    assert section is not None
    assert section.color_space == ColorSpace.CONTINUOUS
    assert section.gradient == [_hex("#000000"), _hex("#FFFFFF")]
    assert section.min_value == "10"
    assert section.max_value == "30"
    # No per-value swatch explosion for continuous colorings.
    assert section.entries == []


def test_to_json_uses_camel_case_wire_format() -> None:
    nodes = [Node(id="0", properties={"score": 10}), Node(id="1", properties={"score": 20})]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.color_nodes(property="score", color_space=ColorSpace.CONTINUOUS, colors=["#000000", "#FFFFFF"])

    section_json = VG.legend.to_json()["nodes"]
    # Fields are snake_case in Python but serialize to the camelCase keys the frontend consumes.
    assert "colorSpace" in section_json
    assert "minValue" in section_json
    assert "maxValue" in section_json
    assert "color_space" not in section_json


def test_color_relationships_populates_legend_independently() -> None:
    nodes = [Node(id="0"), Node(id="1")]
    rels = [
        Relationship(id="r0", source="0", target="1", caption="ACTED_IN"),
        Relationship(id="r1", source="1", target="0", caption="DIRECTED"),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=rels)

    VG.color_nodes(field="id")
    node_section = VG.legend.nodes

    VG.color_relationships(field="caption")

    # Coloring relationships leaves the node section untouched.
    assert VG.legend.nodes == node_section
    rel_section = VG.legend.relationships
    assert rel_section is not None
    assert rel_section.title == "caption"
    assert [entry.label for entry in rel_section.entries] == ["ACTED_IN", "DIRECTED"]


def test_set_legend_overrides_captured_legend() -> None:
    VG = VisualizationGraph(nodes=[Node(id="0", properties={"label": "Movie"})], relationships=[])
    VG.color_nodes(property="label")

    VG.set_legend(nodes={"Movies": "blue", "Directors": "red"})

    section = VG.legend.nodes
    assert section is not None
    assert section.entries == [
        LegendEntry(label="Movies", color=_hex("blue")),
        LegendEntry(label="Directors", color=_hex("red")),
    ]


def test_set_legend_accepts_entry_pairs_and_section() -> None:
    VG = VisualizationGraph(nodes=[Node(id="0")], relationships=[])

    VG.set_legend(
        nodes=[("A", "red"), LegendEntry(label="B", color=_hex("green"))],
        relationships=LegendSection(
            color_space=ColorSpace.DISCRETE, entries=[LegendEntry(label="R", color=_hex("blue"))]
        ),
    )

    assert VG.legend.nodes is not None
    assert [e.label for e in VG.legend.nodes.entries] == ["A", "B"]
    assert VG.legend.relationships is not None
    assert VG.legend.relationships.entries[0].label == "R"


def test_recoloring_refreshes_legend_to_match() -> None:
    # Coloring always refreshes the legend so it reflects the colors currently drawn, even if a
    # manual legend was set beforehand. To keep custom labels, call set_legend after coloring.
    nodes = [Node(id="0", properties={"label": "Movie"}), Node(id="1", properties={"label": "Director"})]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_legend(nodes={"Custom": "blue"})
    VG.color_nodes(property="label")

    section = VG.legend.nodes
    assert section is not None
    assert [entry.label for entry in section.entries] == ["Movie", "Director"]


def test_show_legend_toggles_visibility() -> None:
    VG = VisualizationGraph(nodes=[Node(id="0")], relationships=[])

    VG.show_legend(False)
    assert VG.legend.visible is False

    VG.show_legend(True)
    assert VG.legend.visible is True


def test_non_string_labels_are_stringified() -> None:
    nodes = [
        Node(id="0", properties={"score": 1}),
        Node(id="1", properties={"tags": ["a", "b"]}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.color_nodes(property="score")
    assert VG.legend.nodes is not None
    assert VG.legend.nodes.entries[0].label == "1"

    # list-valued properties are normalized to a hashable and rendered as a readable string.
    VG.color_nodes(property="tags")
    labels = [entry.label for entry in VG.legend.nodes.entries]
    assert "a, b" in labels


def test_render_injects_legend_into_html() -> None:
    VG = VisualizationGraph(nodes=[Node(id="0", properties={"label": "Movie"})], relationships=[])
    VG.color_nodes(property="label")

    html = VG.render().data

    assert "window.__NEO4J_VIZ_DATA__" in html
    assert '"legend"' in html
    assert "Movie" in html


class TestWidgetLegend:
    def test_widget_legend_default(self) -> None:
        widget = GraphWidget()

        assert widget.legend == Legend()

    def test_color_nodes_reassigns_legend_and_fires_observer(self) -> None:
        widget = GraphWidget(nodes=[Node(id="0", properties={"label": "Movie"})])
        changes: list[dict[str, Any]] = []
        widget.observe(lambda change: changes.append(change), names=["legend"])

        widget.color_nodes(property="label")

        assert len(changes) == 1
        assert changes[0]["name"] == "legend"
        assert changes[0]["new"].nodes is not None
        assert changes[0]["new"].nodes.entries[0].label == "Movie"

    def test_legend_trait_json_round_trip(self) -> None:
        widget = GraphWidget(nodes=[Node(id="0", properties={"label": "Movie"})])
        widget.color_nodes(property="label")

        as_json = widget.legend.to_json()
        # to_json must be JSON serializable (it travels to the frontend).
        json.dumps(as_json)
        assert Legend.model_validate(as_json) == widget.legend

    def test_from_graph_data_carries_legend(self) -> None:
        legend = Legend(
            nodes=LegendSection(color_space=ColorSpace.DISCRETE, entries=[LegendEntry(label="A", color=_hex("red"))])
        )

        widget = GraphWidget.from_graph_data([Node(id="0")], [], legend=legend)

        assert widget.legend == legend
