import json
from typing import Any

import pytest

from neo4j_viz import GraphSelection, Node, Relationship, VisualizationGraph, WidgetOptions
from neo4j_viz import streamlit as st_module
from neo4j_viz.streamlit import _RECEIVE_KEYS, _SEND_KEYS, render_widget
from neo4j_viz.widget import GraphWidget


class _FakeComponent:
    """Stand-in for a Streamlit v2 component renderer.

    Records the kwargs it is called with and returns a canned result dict (what the
    frontend would send back via setStateValue, surfaced as a ComponentResult).
    """

    def __init__(self, return_value: dict[str, Any] | None = None) -> None:
        self.return_value = return_value if return_value is not None else {}
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return self.return_value


@pytest.fixture
def widget() -> GraphWidget:
    nodes = [Node(id="0", caption="A"), Node(id="1", caption="B")]
    relationships = [Relationship(source="0", target="1", caption="REL")]
    return VisualizationGraph(nodes=nodes, relationships=relationships).render_widget()


def _patch_component(monkeypatch: pytest.MonkeyPatch, component: _FakeComponent) -> None:
    monkeypatch.setattr(st_module, "_component", lambda: component)


def _patch_session_state(monkeypatch: pytest.MonkeyPatch, state: dict[str, Any]) -> None:
    monkeypatch.setattr(st_module, "_session_state", lambda: state)


def test_sends_serializer_applied_state(monkeypatch: pytest.MonkeyPatch, widget: GraphWidget) -> None:
    component = _FakeComponent()
    _patch_component(monkeypatch, component)

    render_widget(widget, key="g")

    (call,) = component.calls
    assert call["key"] == "g"
    # The v2 renderer receives props as a single `data` dict.
    data = call["data"]
    # Every trait the frontend reads is present...
    assert set(data) == set(_SEND_KEYS)
    # ...and each value is already JSON-serializable, i.e. the to_json serializers ran
    # (the raw Node/WidgetOptions/GraphSelection objects would not be).
    json.dumps(data)
    assert data["nodes"][0] == {"id": "0", "caption": "A", "properties": {}}
    assert isinstance(data["options"], dict)
    assert data["selected"] == {"nodeIds": [], "relationshipIds": []}
    # State keys are declared via on_<name>_change callbacks. Streamlit invokes them
    # with no arguments, so they must be callable with none (regression guard).
    call["on_selected_change"]()
    call["on_options_change"]()


def test_height_forwarded_as_pixels(monkeypatch: pytest.MonkeyPatch) -> None:
    component = _FakeComponent()
    _patch_component(monkeypatch, component)

    widget = VisualizationGraph(nodes=[Node(id="0")], relationships=[]).render_widget(height="400px")
    render_widget(widget)

    (call,) = component.calls
    assert call["height"] == 400


def test_receives_and_deserializes_selection(monkeypatch: pytest.MonkeyPatch, widget: GraphWidget) -> None:
    component = _FakeComponent(return_value={"selected": {"nodeIds": ["0"], "relationshipIds": []}})
    _patch_component(monkeypatch, component)

    result = render_widget(widget)

    # from_json ran: `selected` is a GraphSelection, not a raw dict.
    assert result is widget
    assert isinstance(widget.selected, GraphSelection)
    assert widget.selected.nodeIds == ["0"]


def test_no_interaction_leaves_state_untouched(monkeypatch: pytest.MonkeyPatch, widget: GraphWidget) -> None:
    # Before any interaction the component result carries None values (from `default`).
    component = _FakeComponent(return_value={"selected": None, "options": None})
    _patch_component(monkeypatch, component)

    render_widget(widget)

    assert widget.selected == GraphSelection()


def test_ignores_unexpected_returned_keys(monkeypatch: pytest.MonkeyPatch, widget: GraphWidget) -> None:
    # Only `selected`/`options` may be written back; anything else is dropped so
    # e.g. `nodes` (no from_json) can't clobber the Python-side Node objects.
    assert set(_RECEIVE_KEYS) == {"selected", "options"}
    component = _FakeComponent(return_value={"nodes": [{"id": "bogus"}], "theme": "dark"})
    _patch_component(monkeypatch, component)

    render_widget(widget)

    assert [n.id for n in widget.nodes] == ["0", "1"]
    assert widget.theme == "auto"


def test_rejects_non_widget(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_component(monkeypatch, _FakeComponent())
    with pytest.raises(TypeError, match="Expected a GraphWidget"):
        render_widget("not a widget")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="Expected a GraphWidget"):
        render_widget(VisualizationGraph(nodes=[Node(id="0")], relationships=[]))  # type: ignore[arg-type]


def test_persisted_ui_state_is_carried_into_data(monkeypatch: pytest.MonkeyPatch, widget: GraphWidget) -> None:
    # Simulate the user having changed the layout in a previous run: the new options
    # live in the component's persisted state (st.session_state[key]).
    ui_options = widget.get_state()["options"]
    assert ui_options["layout"] != "hierarchical"  # sanity: differs from what the user picks
    ui_options = {**ui_options, "layout": "hierarchical"}
    _patch_session_state(monkeypatch, {"g": {"options": ui_options, "selected": None}})

    component = _FakeComponent()
    _patch_component(monkeypatch, component)

    render_widget(widget, key="g")

    # The data pushed to the frontend must reflect the user's layout, not the widget's
    # initial one -- otherwise the rerun would reset the UI.
    (call,) = component.calls
    assert call["data"]["options"]["layout"] == "hierarchical"
    # ...and the Python widget reflects it too.
    assert widget.options.layout.value == "hierarchical"


def test_no_persistence_without_key(monkeypatch: pytest.MonkeyPatch, widget: GraphWidget) -> None:
    # Without a key there is no persisted state to read; must not raise.
    _patch_session_state(monkeypatch, {"g": {"options": {"layout": "hierarchical"}}})
    component = _FakeComponent()
    _patch_component(monkeypatch, component)

    render_widget(widget)  # no key

    (call,) = component.calls
    assert call["data"]["options"]["layout"] != "hierarchical"


def test_options_round_trip(monkeypatch: pytest.MonkeyPatch, widget: GraphWidget) -> None:
    options_json = widget.get_state()["options"]
    component = _FakeComponent(return_value={"options": options_json})
    _patch_component(monkeypatch, component)

    result = render_widget(widget)
    # from_json turned the frontend options dict back into a WidgetOptions.
    assert isinstance(result.options, WidgetOptions)
