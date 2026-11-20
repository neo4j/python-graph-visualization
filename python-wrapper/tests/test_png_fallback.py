from typing import Any
from unittest.mock import Mock

import pytest

from neo4j_viz import GraphWidget, Node, Relationship, VisualizationGraph
from neo4j_viz._fallback_outputs import MAX_BYTES, PNG_META

_PNG_DATA_URL = f"{PNG_META},QUJD"
_OVERSIZED_DATA_URL = f"{PNG_META}," + "A" * ((MAX_BYTES + 1) * 4 // 3)


def _make_widget(**kwargs: Any) -> GraphWidget:
    return GraphWidget(
        nodes=[Node(id="n1", caption="A"), Node(id="n2", caption="B")],
        relationships=[Relationship(source="n1", target="n2", caption="LINKS")],
        **kwargs,
    )


def _capture_display(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Capture every `display` call, from the widget bundle and the fallback slots alike."""
    calls: list[dict[str, Any]] = []

    def record(data: Any, **kwargs: Any) -> None:
        calls.append({"data": data, **kwargs})

    monkeypatch.setattr("neo4j_viz.widget.display", record)
    monkeypatch.setattr("neo4j_viz._fallback_outputs.display", record)
    return calls


def _capture_update_display(monkeypatch: pytest.MonkeyPatch) -> Mock:
    updates = Mock(name="update_display")
    monkeypatch.setattr("neo4j_viz._fallback_outputs.update_display", updates)
    return updates


def _widget_with_slots(monkeypatch: pytest.MonkeyPatch, slots: int = 1) -> tuple[GraphWidget, Mock, list[str]]:
    """A widget displayed `slots` times, with its snapshot storage captured."""
    display_calls = _capture_display(monkeypatch)
    updates = _capture_update_display(monkeypatch)
    widget = _make_widget()
    for _ in range(slots):
        widget._ipython_display_()
    slot_ids = [call["display_id"] for call in display_calls if call["data"] == {"text/plain": ""}]
    assert len(slot_ids) == slots
    return widget, updates, slot_ids


class TestIpythonDisplay:
    def test_displays_an_image_slot_before_the_widget(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = _capture_display(monkeypatch)

        widget = _make_widget()
        widget._ipython_display_()

        assert len(calls) == 2
        slot, bundle = calls
        assert slot["data"] == {"text/plain": ""}
        assert slot["raw"] is True
        assert isinstance(slot["display_id"], str)
        # the widget's own output is displayed unchanged
        assert bundle["data"]["application/vnd.jupyter.widget-view+json"]["model_id"] == widget._model_id

    def test_skips_the_slot_when_the_fallback_is_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = _capture_display(monkeypatch)

        _make_widget(fallback=False)._ipython_display_()

        assert len(calls) == 1

    def test_registers_a_slot_per_display(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _, _, slot_ids = _widget_with_slots(monkeypatch, slots=2)

        assert len(set(slot_ids)) == 2


class TestSnapshotStorage:
    def test_stores_the_snapshot_in_every_slot(self, monkeypatch: pytest.MonkeyPatch) -> None:
        widget, updates, slot_ids = _widget_with_slots(monkeypatch, slots=2)

        widget._on_frontend_msg(widget, {"kind": "snapshot", "dataUrl": _PNG_DATA_URL}, [])

        assert updates.call_count == 2
        for call, slot_id in zip(updates.call_args_list, slot_ids):
            assert call.args[0] == {"image/png": "QUJD", "text/plain": "Graph visualization"}
            assert call.kwargs == {"raw": True, "display_id": slot_id}

    def test_ignores_payloads_that_are_not_png_data_urls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        widget, updates, _ = _widget_with_slots(monkeypatch)

        for message in (
            {"kind": "snapshot", "dataUrl": "data:image/svg+xml;charset=utf-8,%3Csvg%3E"},
            {"kind": "snapshot", "dataUrl": "not-a-data-url"},
            {"kind": "snapshot", "dataUrl": "data:image/png;base64"},
            {"kind": "snapshot", "dataUrl": 42},
            {"kind": "snapshot"},
        ):
            widget._on_frontend_msg(widget, message, [])

        updates.assert_not_called()

    def test_drops_an_oversized_snapshot(self, monkeypatch: pytest.MonkeyPatch) -> None:
        widget, updates, _ = _widget_with_slots(monkeypatch)

        with pytest.warns(UserWarning, match="Skipping the static PNG fallback"):
            widget._on_frontend_msg(widget, {"kind": "snapshot", "dataUrl": _OVERSIZED_DATA_URL}, [])

        updates.assert_not_called()

    def test_warns_only_once_about_oversized_snapshots(self, monkeypatch: pytest.MonkeyPatch) -> None:
        widget, _, _ = _widget_with_slots(monkeypatch)

        with pytest.warns(UserWarning) as record:
            for _ in range(2):
                widget._on_frontend_msg(widget, {"kind": "snapshot", "dataUrl": _OVERSIZED_DATA_URL}, [])

        assert len(record) == 1

    def test_keeps_the_last_good_snapshot(self, monkeypatch: pytest.MonkeyPatch) -> None:
        widget, updates, _ = _widget_with_slots(monkeypatch)

        widget._on_frontend_msg(widget, {"kind": "snapshot", "dataUrl": _PNG_DATA_URL}, [])
        with pytest.warns(UserWarning):
            widget._on_frontend_msg(widget, {"kind": "snapshot", "dataUrl": _OVERSIZED_DATA_URL}, [])

        # the earlier image stays stored rather than being replaced or cleared
        assert updates.call_count == 1

    def test_does_nothing_without_a_slot(self, monkeypatch: pytest.MonkeyPatch) -> None:
        widget, updates, _ = _widget_with_slots(monkeypatch, slots=0)

        widget._on_frontend_msg(widget, {"kind": "snapshot", "dataUrl": _PNG_DATA_URL}, [])

        updates.assert_not_called()


class TestFrontendMessageRouting:
    def test_ignores_unrelated_messages(self, monkeypatch: pytest.MonkeyPatch) -> None:
        widget, updates, _ = _widget_with_slots(monkeypatch)

        widget._on_frontend_msg(widget, {"kind": "something_else"}, [])
        widget._on_frontend_msg(widget, "not-a-dict", [])

        updates.assert_not_called()


class TestRenderWidgetFallback:
    def test_is_enabled_by_default(self) -> None:
        graph = VisualizationGraph(nodes=[Node(id="n1")], relationships=[])

        assert graph.render_widget().fallback is True

    def test_can_be_disabled(self) -> None:
        graph = VisualizationGraph(nodes=[Node(id="n1")], relationships=[])

        assert graph.render_widget(fallback=False).fallback is False

    def test_can_be_changed_on_the_widget(self) -> None:
        widget = _make_widget()

        widget.fallback = False

        assert widget.fallback is False
