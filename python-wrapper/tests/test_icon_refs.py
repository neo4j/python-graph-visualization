from typing import Any

from comm.base_comm import BaseComm

from neo4j_viz import Node, OverlayIcon, Relationship, VisualizationGraph
from neo4j_viz._icon_refs import apply_icon_refs, build_icon_refs
from neo4j_viz.widget import GraphWidget

_LONG_ICON = "data:image/svg+xml," + "A" * 400
_LONG_PNG = "data:image/png;base64," + "B" * 400


def test_build_icon_refs_dedupes_shared_data_uri() -> None:
    nodes = [Node(id="0", icon=_LONG_ICON), Node(id="1", icon=_LONG_ICON)]

    refs, uri_to_ref = build_icon_refs(nodes, [])

    assert refs == {"#0": _LONG_ICON}
    assert uri_to_ref == {_LONG_ICON: "#0"}


def test_build_icon_refs_ignores_short_and_non_data_values() -> None:
    nodes = [
        Node(id="0", icon="database_check"),
        Node(id="1", icon="https://example.com/icon.svg"),
        Node(id="2", icon="data:image/svg+xml,short"),
    ]

    refs, uri_to_ref = build_icon_refs(nodes, [])

    assert refs == {}
    assert uri_to_ref == {}


def test_build_icon_refs_factors_overlay_icons() -> None:
    nodes = [Node(id="0", overlay_icon=OverlayIcon(url=_LONG_ICON))]
    relationships = [Relationship(source="0", target="1", overlay_icon=OverlayIcon(url=_LONG_PNG))]

    refs, _ = build_icon_refs(nodes, relationships)

    assert refs == {"#0": _LONG_ICON, "#1": _LONG_PNG}


def test_apply_icon_refs_replaces_icon_and_overlay() -> None:
    entity: dict[str, Any] = {"id": "0", "icon": _LONG_ICON, "overlayIcon": {"url": _LONG_ICON}}

    result = apply_icon_refs(entity, {_LONG_ICON: "#0"})

    assert result["icon"] == "#0"
    assert result["overlayIcon"]["url"] == "#0"


def test_apply_icon_refs_leaves_other_values() -> None:
    entity: dict[str, Any] = {"id": "0", "icon": "database_check"}

    assert apply_icon_refs(entity, {_LONG_ICON: "#0"})["icon"] == "database_check"


def test_apply_icon_refs_does_not_mutate_input() -> None:
    entity: dict[str, Any] = {"id": "0", "icon": _LONG_ICON, "overlayIcon": {"url": _LONG_ICON}}

    result = apply_icon_refs(entity, {_LONG_ICON: "#0"})

    assert result is not entity
    assert entity["icon"] == _LONG_ICON
    assert entity["overlayIcon"]["url"] == _LONG_ICON


def test_widget_serializes_shared_icons_as_refs() -> None:
    widget = GraphWidget(nodes=[Node(id="0", icon=_LONG_ICON), Node(id="1", icon=_LONG_ICON)])

    assert widget._icon_refs == {"#0": _LONG_ICON}
    state = widget.get_state("nodes")
    assert [node["icon"] for node in state["nodes"]] == ["#0", "#0"]


def test_widget_full_state_includes_icon_refs() -> None:
    widget = GraphWidget(nodes=[Node(id="0", icon=_LONG_ICON)])

    assert widget.get_state()["_icon_refs"] == {"#0": _LONG_ICON}


class _RecordingComm(BaseComm):
    kernel = True

    def __init__(self) -> None:
        self.messages: list[Any] = []
        super().__init__()

    def publish_msg(
        self, msg_type: str, data: Any = None, metadata: Any = None, buffers: Any = None, **keys: Any
    ) -> None:
        self.messages.append(data)


def test_icon_refs_are_sent_before_the_entities() -> None:
    widget = GraphWidget(nodes=[Node(id="0")])
    widget.comm = _RecordingComm()
    widget.comm.messages.clear()

    # Changing the entities changes the table, so both must be pushed.
    widget.nodes = [Node(id="0", icon=_LONG_ICON)]

    updates = [m["state"] for m in widget.comm.messages if m and m.get("method") == "update"]
    keys = [sorted(state) for state in updates]
    # The table must reach the frontend before the entities that reference it.
    assert keys.index(["_icon_refs"]) < keys.index(["nodes"])


def test_render_inlines_shared_icons_once() -> None:
    nodes = [Node(id=str(i), icon=_LONG_ICON) for i in range(3)]

    html = VisualizationGraph(nodes=nodes, relationships=[]).render()

    assert html.data.count(_LONG_ICON) == 1
    assert "_icon_refs" in html.data
