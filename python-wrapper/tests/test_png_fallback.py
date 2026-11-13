from typing import Any
from unittest.mock import Mock

import pytest

from neo4j_viz import GraphWidget, Node, Relationship, VisualizationGraph
from neo4j_viz.widget import _FALLBACK_MAX_BYTES, _FALLBACK_PNG_PREFIX

_PNG_DATA_URL = "data:image/png;base64,QUJD"
_OVERSIZED_DATA_URL = _FALLBACK_PNG_PREFIX + "A" * ((_FALLBACK_MAX_BYTES + 1) * 4 // 3)


def _make_widget(**kwargs: Any) -> GraphWidget:
    return GraphWidget(
        nodes=[Node(id="n1", caption="A"), Node(id="n2", caption="B")],
        relationships=[Relationship(source="n1", target="n2", caption="LINKS")],
        **kwargs,
    )


def _widget_with_slots(
    monkeypatch: pytest.MonkeyPatch, slots: tuple[str, ...] = ("slot-1",)
) -> tuple[GraphWidget, Mock]:
    updates = Mock(name="update_display")
    monkeypatch.setattr("IPython.display.update_display", updates)
    widget = _make_widget()
    widget._image_slot_ids = list(slots)
    return widget, updates


class TestIpythonDisplay:
    def test_displays_an_image_slot_before_the_widget(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict[str, Any]] = []
        monkeypatch.setattr("IPython.display.display", lambda data, **kwargs: calls.append({"data": data, **kwargs}))

        widget = _make_widget()
        widget._ipython_display_()

        assert len(calls) == 2
        slot, bundle = calls
        assert slot["data"] == {"text/plain": ""}
        assert slot["raw"] is True
        assert slot["display_id"] == widget._image_slot_ids[0]
        # the widget's own output is displayed unchanged
        assert bundle["data"]["application/vnd.jupyter.widget-view+json"]["model_id"] == widget._model_id

    def test_skips_the_slot_when_the_fallback_is_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[Any] = []
        monkeypatch.setattr("IPython.display.display", lambda data, **kwargs: calls.append(data))

        widget = _make_widget(fallback=False)
        widget._ipython_display_()

        assert len(calls) == 1
        assert widget._image_slot_ids == []

    def test_registers_a_slot_per_display(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("IPython.display.display", lambda data, **kwargs: None)

        widget = _make_widget()
        widget._ipython_display_()
        widget._ipython_display_()

        assert len(widget._image_slot_ids) == 2


class TestOnSnapshot:
    def test_stores_the_snapshot_in_every_slot(self, monkeypatch: pytest.MonkeyPatch) -> None:
        widget, updates = _widget_with_slots(monkeypatch, slots=("slot-1", "slot-2"))

        widget._on_snapshot({"dataUrl": _PNG_DATA_URL})

        assert updates.call_count == 2
        for call, slot_id in zip(updates.call_args_list, ("slot-1", "slot-2")):
            assert call.args[0] == {"image/png": "QUJD", "text/plain": "Graph visualization"}
            assert call.kwargs == {"raw": True, "display_id": slot_id}

    def test_ignores_payloads_that_are_not_png_data_urls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        widget, updates = _widget_with_slots(monkeypatch)

        widget._on_snapshot({"dataUrl": "data:image/svg+xml;charset=utf-8,%3Csvg%3E"})
        widget._on_snapshot({"dataUrl": "not-a-data-url"})
        widget._on_snapshot({"dataUrl": 42})
        widget._on_snapshot({})

        updates.assert_not_called()

    def test_drops_an_oversized_snapshot(self, monkeypatch: pytest.MonkeyPatch) -> None:
        widget, updates = _widget_with_slots(monkeypatch)

        with pytest.warns(UserWarning, match="Skipping the static PNG fallback"):
            widget._on_snapshot({"dataUrl": _OVERSIZED_DATA_URL})

        updates.assert_not_called()

    def test_warns_only_once_about_oversized_snapshots(self, monkeypatch: pytest.MonkeyPatch) -> None:
        widget, _ = _widget_with_slots(monkeypatch)

        with pytest.warns(UserWarning) as record:
            widget._on_snapshot({"dataUrl": _OVERSIZED_DATA_URL})
            widget._on_snapshot({"dataUrl": _OVERSIZED_DATA_URL})

        assert len(record) == 1

    def test_keeps_the_last_good_snapshot(self, monkeypatch: pytest.MonkeyPatch) -> None:
        widget, updates = _widget_with_slots(monkeypatch)

        widget._on_snapshot({"dataUrl": _PNG_DATA_URL})
        with pytest.warns(UserWarning):
            widget._on_snapshot({"dataUrl": _OVERSIZED_DATA_URL})

        # the earlier image stays stored rather than being replaced or cleared
        assert updates.call_count == 1

    def test_does_nothing_without_a_slot(self, monkeypatch: pytest.MonkeyPatch) -> None:
        widget, updates = _widget_with_slots(monkeypatch, slots=())

        widget._on_snapshot({"dataUrl": _PNG_DATA_URL})

        updates.assert_not_called()


class TestFrontendMessageRouting:
    def test_routes_snapshot_messages(self, monkeypatch: pytest.MonkeyPatch) -> None:
        widget, updates = _widget_with_slots(monkeypatch)

        widget._on_frontend_msg(widget, {"kind": "snapshot", "dataUrl": _PNG_DATA_URL}, [])

        assert updates.call_count == 1

    def test_ignores_unrelated_messages(self, monkeypatch: pytest.MonkeyPatch) -> None:
        widget, updates = _widget_with_slots(monkeypatch)

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
