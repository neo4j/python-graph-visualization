from typing import Any

import pytest

from neo4j_viz import GraphSelection, Node, Relationship, VisualizationGraph, WidgetOptions
from neo4j_viz import streamlit as st_module
from neo4j_viz.options import InteractionEvent, WidgetLayout
from neo4j_viz.streamlit import _RECEIVE_KEYS, _SEND_KEYS, display_widget
from neo4j_viz.widget import GraphWidget


class _FakeComponent:
    def __init__(self) -> None:
        self.return_value: dict[str, Any] = {}
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return self.return_value

    @property
    def call(self) -> dict[str, Any]:
        """The single call's kwargs, asserting exactly one render happened."""
        (call,) = self.calls
        return call


@pytest.fixture
def widget() -> GraphWidget:
    nodes = [Node(id="0", caption="A"), Node(id="1", caption="B")]
    relationships = [Relationship(source="0", target="1", caption="REL")]
    return VisualizationGraph(nodes=nodes, relationships=relationships).render_widget()


@pytest.fixture
def component(monkeypatch: pytest.MonkeyPatch) -> _FakeComponent:
    """Replace the real Streamlit v2 renderer (needs a Streamlit runtime) with a fake."""
    fake = _FakeComponent()
    monkeypatch.setattr(st_module, "_component_renderer", lambda: fake)
    return fake


@pytest.fixture
def session_state(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Stub Streamlit's ``session_state`` with a plain dict tests can populate."""
    state: dict[str, Any] = {}
    monkeypatch.setattr("streamlit.session_state", state)
    return state


def test_sends_serializer_applied_state(component: _FakeComponent, widget: GraphWidget) -> None:
    display_widget(widget, key="g")

    assert component.call["key"] == "g"
    data = component.call["data"]

    assert set(data) == set(_SEND_KEYS)
    assert data["nodes"][0] == {"id": "0", "caption": "A", "properties": {}}
    assert isinstance(data["options"], dict)
    assert data["selected"] == {"nodeIds": [], "relationshipIds": []}


def test_height_forwarded_as_pixels(component: _FakeComponent) -> None:
    widget = VisualizationGraph(nodes=[Node(id="0")], relationships=[]).render_widget(height="400px")
    display_widget(widget)

    assert component.call["height"] == 400


def test_receives_and_deserializes_selection(component: _FakeComponent, widget: GraphWidget) -> None:
    component.return_value = {"selected": {"nodeIds": ["0"], "relationshipIds": []}}

    display_widget(widget)

    # display_widget syncs in place; read the state off the passed-in widget.
    assert widget.selected.nodeIds == ["0"]


def test_no_interaction_leaves_state_untouched(component: _FakeComponent, widget: GraphWidget) -> None:
    # Before any interaction the component result carries None values (from `default`).
    component.return_value = {"selected": None, "options": None}

    display_widget(widget)
    assert widget.selected == GraphSelection()


def test_ignores_unexpected_returned_keys(component: _FakeComponent, widget: GraphWidget) -> None:
    assert set(_RECEIVE_KEYS) == {"selected", "options", "last_event"}
    component.return_value = {"nodes": [{"id": "bogus"}], "theme": "dark"}

    display_widget(widget)

    assert [n.id for n in widget.nodes] == ["0", "1"]
    assert widget.theme == "auto"


def test_receives_and_deserializes_last_event(component: _FakeComponent, widget: GraphWidget) -> None:
    component.return_value = {"last_event": {"type": "node_click", "id": "0"}}

    display_widget(widget)

    assert isinstance(widget.last_event, InteractionEvent)
    assert widget.last_event.type == "node_click"
    assert widget.last_event.id == "0"


def test_rejects_non_widget() -> None:
    with pytest.raises(TypeError, match="Expected a GraphWidget"):
        display_widget("not a widget")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="Expected a GraphWidget"):
        display_widget(VisualizationGraph(nodes=[Node(id="0")], relationships=[]))  # type: ignore[arg-type]


def test_persisted_ui_state_is_carried_into_data(
    component: _FakeComponent, session_state: dict[str, Any], widget: GraphWidget
) -> None:
    # Simulate the user having changed the layout in a previous run
    ui_options = widget.get_state()["options"]
    session_state["g"] = {"options": {**ui_options, "layout": "hierarchical"}, "selected": None}

    display_widget(widget, key="g")

    # check the layout is not reset
    assert component.call["data"]["options"]["layout"] == "hierarchical"
    assert widget.options.layout == WidgetLayout.HIERARCHICAL


def test_options_round_trip(component: _FakeComponent, widget: GraphWidget) -> None:
    component.return_value = {"options": widget.get_state()["options"]}

    display_widget(widget)
    # from_json turned the frontend options dict back into a WidgetOptions.
    assert isinstance(widget.options, WidgetOptions)
