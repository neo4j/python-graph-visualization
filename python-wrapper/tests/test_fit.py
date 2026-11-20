import asyncio
from typing import Any
from unittest.mock import Mock

import pytest

from neo4j_viz import GraphWidget, Node, Relationship


def _make_widget() -> GraphWidget:
    return GraphWidget(
        nodes=[Node(id="n1", caption="A"), Node(id="n2", caption="B")],
        relationships=[Relationship(source="n1", target="n2", caption="LINKS")],
    )


def _fake_frontend(widget: GraphWidget, response_for_request: Any) -> Mock:
    """Make `widget` look connected to a live kernel and reply to fit requests like the JS frontend.

    `response_for_request` is called with the `fit` content captured from `widget.send`; its
    return value is delivered back through the widget's custom-message dispatcher
    (`_on_frontend_msg`), i.e. the same path a real comm message takes.
    """
    widget.comm = Mock(name="comm")
    comm = widget.comm
    comm.kernel = Mock(name="kernel")  # non-None kernel, mirroring a live ipykernel comm
    widget._nvl_ready = True  # the frontend signals readiness once the view is mounted

    def fake_send(content: dict[str, Any], buffers: Any = None) -> None:
        if content.get("kind") != "fit":
            return
        reply = dict(response_for_request(content))
        reply["id"] = content["id"]
        loop = asyncio.get_running_loop()
        loop.call_soon(widget._on_frontend_msg, widget, reply, [])

    widget.send = fake_send
    return widget


class TestFit:
    def test_fit_round_trip(self) -> None:
        requests: list[dict[str, Any]] = []

        def respond(request: dict[str, Any]) -> dict[str, Any]:
            requests.append(request)
            return {"kind": "fit_response"}

        widget = _fake_frontend(_make_widget(), respond)

        asyncio.run(widget.fit())

        assert len(requests) == 1
        assert requests[0]["kind"] == "fit"
        assert isinstance(requests[0]["id"], str)
        # No ids means every node in the graph.
        assert "nodeIds" not in requests[0]

    def test_fit_frames_the_given_node_ids(self) -> None:
        requests: list[dict[str, Any]] = []

        def respond(request: dict[str, Any]) -> dict[str, Any]:
            requests.append(request)
            return {"kind": "fit_response"}

        widget = _fake_frontend(_make_widget(), respond)

        asyncio.run(widget.fit(["n2"]))

        assert requests[0]["nodeIds"] == ["n2"]

    def test_fit_converts_node_ids_to_strings(self) -> None:
        # The frontend matches node ids as strings, whatever the Python-side id type.
        requests: list[dict[str, Any]] = []

        def respond(request: dict[str, Any]) -> dict[str, Any]:
            requests.append(request)
            return {"kind": "fit_response"}

        widget = _fake_frontend(GraphWidget(nodes=[Node(id=0), Node(id=1)]), respond)

        asyncio.run(widget.fit([1]))

        assert requests[0]["nodeIds"] == ["1"]

    def test_fit_rejects_unknown_node_ids(self) -> None:
        widget = _fake_frontend(_make_widget(), lambda request: {"kind": "fit_response"})

        with pytest.raises(ValueError, match="Unknown node ids: nope, other"):
            asyncio.run(widget.fit(["n1", "nope", "other"]))

    def test_fit_rejects_an_empty_node_id_list(self) -> None:
        widget = _fake_frontend(_make_widget(), lambda request: {"kind": "fit_response"})

        with pytest.raises(ValueError, match="`node_ids` is empty"):
            asyncio.run(widget.fit([]))

    def test_fit_raises_frontend_error(self) -> None:
        widget = _fake_frontend(_make_widget(), lambda request: {"kind": "fit_response", "error": "boom"})

        with pytest.raises(RuntimeError, match="boom"):
            asyncio.run(widget.fit())

    def test_fit_times_out_without_frontend_reply(self) -> None:
        widget = _fake_frontend(_make_widget(), lambda request: None)
        # A reply of None never dispatches a response; fit() must hit its timeout.
        widget.send = lambda content, buffers=None: None

        with pytest.raises(TimeoutError, match="timed out"):
            asyncio.run(widget.fit(timeout=0.05))

    def test_fit_requires_live_frontend(self) -> None:
        # No comm at all: the request would silently go nowhere, so it fails fast.
        widget = _make_widget()

        with pytest.raises(RuntimeError, match=r"GraphWidget\.fit\(\) requires a live notebook frontend"):
            asyncio.run(widget.fit())

    def test_fit_waits_for_frontend_ready(self) -> None:
        requests: list[dict[str, Any]] = []

        def respond(request: dict[str, Any]) -> dict[str, Any]:
            requests.append(request)
            return {"kind": "fit_response"}

        widget = _fake_frontend(_make_widget(), respond)
        widget._nvl_ready = False  # frontend not ready yet

        async def run() -> None:
            asyncio.get_running_loop().call_later(0.05, setattr, widget, "_nvl_ready", True)
            await widget.fit(timeout=5.0)

        asyncio.run(run())

        assert len(requests) == 1

    def test_fit_times_out_waiting_for_frontend_ready(self) -> None:
        requests: list[dict[str, Any]] = []

        def respond(request: dict[str, Any]) -> dict[str, Any]:
            requests.append(request)
            return {"kind": "fit_response"}

        widget = _fake_frontend(_make_widget(), respond)
        widget._nvl_ready = False

        with pytest.raises(TimeoutError, match="did not finish rendering"):
            asyncio.run(widget.fit(timeout=0.05))

        # nothing sent while the frontend is not ready
        assert requests == []

    def test_fit_ignores_a_response_of_another_kind(self) -> None:
        # A save_response for a fit request id belongs to no pending fit and is dropped.
        widget = _fake_frontend(_make_widget(), lambda request: {"kind": "save_response", "dataUrl": "AAA"})

        with pytest.raises(TimeoutError, match="timed out"):
            asyncio.run(widget.fit(timeout=0.05))
