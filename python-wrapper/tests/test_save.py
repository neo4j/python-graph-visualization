import asyncio
import base64
import pathlib
from typing import Any
from unittest.mock import Mock

import pytest

from neo4j_viz import GraphWidget, Node, Relationship
from neo4j_viz.widget import _decode_data_url, _resolve_save_format


def _make_widget() -> GraphWidget:
    return GraphWidget(
        nodes=[Node(id="n1", caption="A"), Node(id="n2", caption="B")],
        relationships=[Relationship(source="n1", target="n2", caption="LINKS")],
    )


def _fake_frontend(widget: GraphWidget, response_for_request: Any) -> Mock:
    """Make `widget` look connected to a live kernel and reply to save requests like the JS frontend.

    `response_for_request` is called with the `save_request` content captured from
    `widget.send`; its return value is delivered back through the widget's custom-message
    dispatcher (`_on_frontend_msg`), i.e. the same path a real comm message takes.
    """
    widget.comm = Mock(name="comm")
    comm = widget.comm
    comm.kernel = Mock(name="kernel")  # non-None kernel, mirroring a live ipykernel comm

    def fake_send(content: dict[str, Any], buffers: Any = None) -> None:
        if content.get("kind") != "save_request":
            return
        reply = dict(response_for_request(content))
        reply["id"] = content["id"]
        loop = asyncio.get_running_loop()
        loop.call_soon(widget._on_frontend_msg, widget, reply, [])

    widget.send = fake_send
    return widget


class TestResolveSaveFormat:
    def test_infers_from_png_suffix(self) -> None:
        assert _resolve_save_format(pathlib.Path("graph.png"), None) == "png"

    def test_infers_from_svg_suffix(self) -> None:
        assert _resolve_save_format(pathlib.Path("graph.svg"), None) == "svg"

    def test_defaults_to_svg_without_suffix(self) -> None:
        assert _resolve_save_format(pathlib.Path("graph"), None) == "svg"

    def test_unknown_suffix_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot infer the save format"):
            _resolve_save_format(pathlib.Path("graph.txt"), None)

    def test_explicit_format_without_suffix(self) -> None:
        assert _resolve_save_format(pathlib.Path("graph"), "png") == "png"

    def test_explicit_format_matching_suffix(self) -> None:
        assert _resolve_save_format(pathlib.Path("graph.svg"), "svg") == "svg"

    def test_explicit_format_is_case_insensitive(self) -> None:
        assert _resolve_save_format(pathlib.Path("graph.PNG"), "PNG") == "png"  # type: ignore[arg-type]

    def test_conflicting_format_and_suffix_raises(self) -> None:
        with pytest.raises(ValueError, match="does not match the format"):
            _resolve_save_format(pathlib.Path("graph.png"), "svg")

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid save format"):
            _resolve_save_format(pathlib.Path("graph"), "jpeg")  # type: ignore[arg-type]


class TestDecodeDataUrl:
    def test_decodes_base64_png(self) -> None:
        payload = base64.b64encode(b"\x89PNG-bytes").decode()
        assert _decode_data_url(f"data:image/png;base64,{payload}") == b"\x89PNG-bytes"

    def test_decodes_url_encoded_svg(self) -> None:
        data_url = "data:image/svg+xml;charset=utf-8,%3Csvg%3Ehello%3C%2Fsvg%3E"
        assert _decode_data_url(data_url) == b"<svg>hello</svg>"

    def test_rejects_non_data_url(self) -> None:
        with pytest.raises(ValueError, match="unexpected image payload"):
            _decode_data_url("not-a-data-url")


class TestSave:
    def test_save_png_round_trip(self, tmp_path: pathlib.Path) -> None:
        widget = _fake_frontend(
            _make_widget(),
            lambda request: {
                "kind": "save_response",
                "dataUrl": "data:image/png;base64," + base64.b64encode(b"\x89PNG-data").decode(),
            },
        )

        result = asyncio.run(widget.save(tmp_path / "graph.png"))

        assert result == tmp_path / "graph.png"
        assert (tmp_path / "graph.png").read_bytes() == b"\x89PNG-data"

    def test_save_svg_round_trip(self, tmp_path: pathlib.Path) -> None:
        widget = _fake_frontend(
            _make_widget(),
            lambda request: {
                "kind": "save_response",
                "dataUrl": "data:image/svg+xml;charset=utf-8,%3Csvg%3Ehi%3C%2Fsvg%3E",
            },
        )

        result = asyncio.run(widget.save(tmp_path / "graph.svg"))

        assert result == tmp_path / "graph.svg"
        assert (tmp_path / "graph.svg").read_text(encoding="utf-8") == "<svg>hi</svg>"

    def test_save_passes_request_options(self, tmp_path: pathlib.Path) -> None:
        requests: list[dict[str, Any]] = []

        def respond(request: dict[str, Any]) -> dict[str, Any]:
            requests.append(request)
            return {"kind": "save_response", "dataUrl": "data:image/png;base64," + base64.b64encode(b"x").decode()}

        widget = _fake_frontend(_make_widget(), respond)

        asyncio.run(widget.save(tmp_path / "graph.png", background_color="#ffffff", timeout=5.0))

        assert len(requests) == 1
        assert requests[0]["kind"] == "save_request"
        assert requests[0]["format"] == "png"
        assert requests[0]["backgroundColor"] == "#ffffff"
        assert isinstance(requests[0]["id"], str)

    def test_save_defaults_to_svg(self, tmp_path: pathlib.Path) -> None:
        requests: list[dict[str, Any]] = []

        def respond(request: dict[str, Any]) -> dict[str, Any]:
            requests.append(request)
            return {"kind": "save_response", "dataUrl": "data:image/svg+xml;charset=utf-8,%3Csvg%3E%3C%2Fsvg%3E"}

        widget = _fake_frontend(_make_widget(), respond)

        asyncio.run(widget.save(tmp_path / "graph"))

        assert requests[0]["format"] == "svg"

    def test_save_raises_frontend_error(self, tmp_path: pathlib.Path) -> None:
        widget = _fake_frontend(_make_widget(), lambda request: {"kind": "save_response", "error": "boom"})

        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(widget.save(tmp_path / "graph.png"))

    def test_save_raises_on_missing_data_url(self, tmp_path: pathlib.Path) -> None:
        widget = _fake_frontend(_make_widget(), lambda request: {"kind": "save_response"})

        with pytest.raises(RuntimeError, match="Unexpected save response"):
            asyncio.run(widget.save(tmp_path / "graph.png"))

    def test_save_times_out_without_frontend_reply(self, tmp_path: pathlib.Path) -> None:
        widget = _fake_frontend(_make_widget(), lambda request: None)
        # A reply of None never dispatches a response; save() must hit its timeout.
        widget.send = lambda content, buffers=None: None

        with pytest.raises(TimeoutError, match="timed out"):
            asyncio.run(widget.save(tmp_path / "graph.png", timeout=0.05))

    def test_save_fails_fast_without_live_kernel(self, tmp_path: pathlib.Path) -> None:
        # Outside a kernel (as in these tests) the widget holds a DummyComm.
        widget = _make_widget()

        with pytest.raises(RuntimeError, match="requires a live notebook frontend"):
            asyncio.run(widget.save(tmp_path / "graph.png"))

    def test_save_validates_format_before_frontend_check(self, tmp_path: pathlib.Path) -> None:
        widget = _fake_frontend(_make_widget(), lambda request: None)

        with pytest.raises(ValueError, match="does not match the format"):
            asyncio.run(widget.save(tmp_path / "graph.png", format="svg"))

    def test_dispatcher_ignores_unrelated_messages(self) -> None:
        widget = _make_widget()
        widget._pending_save_requests = {}
        # Neither an unrelated kind nor an unknown request id may raise.
        widget._on_frontend_msg(widget, {"kind": "something_else", "id": "x"}, [])
        widget._on_frontend_msg(widget, {"kind": "save_response", "id": "unknown"}, [])
        widget._on_frontend_msg(widget, "not-a-dict", [])

    def test_pending_requests_are_cleaned_up(self, tmp_path: pathlib.Path) -> None:
        widget = _fake_frontend(_make_widget(), lambda request: None)
        widget.send = lambda content, buffers=None: None

        with pytest.raises(TimeoutError):
            asyncio.run(widget.save(tmp_path / "graph.png", timeout=0.05))

        assert widget._pending_save_requests == {}
