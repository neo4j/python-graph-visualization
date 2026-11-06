import email.message
import re
import warnings
from pathlib import Path
from urllib.error import HTTPError

import pytest

import neo4j_viz.icons as icons_module
from neo4j_viz import (
    Icons,
    Node,
    VisualizationGraph,
    icon_from_file,
    icon_from_svg,
    icon_from_url,
    icons_from_directory,
)


def test_set_node_icons_explicit() -> None:
    nodes = [Node(id="1"), Node(id="2"), Node(id="3")]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_icons(icons={"1": Icons.CIRCLE, "2": "https://example.com/icon.svg"})

    assert VG.nodes[0].icon == Icons.CIRCLE
    assert VG.nodes[1].icon == "https://example.com/icon.svg"
    assert VG.nodes[2].icon is None


def test_set_node_icons_from_property() -> None:
    nodes = [
        Node(id="1", properties={"icon": "Circle"}),
        Node(id="2", properties={"icon": "Square"}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_icons(property="icon")

    assert VG.nodes[0].icon == "Circle"
    assert VG.nodes[1].icon == "Square"


def test_set_node_icons_from_property_with_mapping() -> None:
    nodes = [
        Node(id="1", properties={"label": "Person"}),
        Node(id="2", properties={"label": "Company"}),
        Node(id="3", properties={"label": "Other"}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_icons(property="label", mapping={"Person": Icons.USER_SHIELD, "Company": Icons.DEPLOYMENTS})

    assert VG.nodes[0].icon == Icons.USER_SHIELD
    assert VG.nodes[1].icon == Icons.DEPLOYMENTS
    assert VG.nodes[2].icon is None  # no mapping entry


def test_set_node_icons_from_field() -> None:
    nodes = [Node(id="1", caption="Circle"), Node(id="2", caption="Square")]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_icons(field="caption")

    assert VG.nodes[0].icon == "Circle"
    assert VG.nodes[1].icon == "Square"


def test_set_node_icons_field_with_snake_case() -> None:
    nodes = [Node(id="1", caption="Circle")]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_icons(field="caption")

    assert VG.nodes[0].icon == "Circle"


def test_set_node_icons_override_false() -> None:
    nodes = [
        Node(id="1", icon=Icons.CIRCLE),
        Node(id="2"),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_icons(icons={"1": Icons.SQUARE, "2": Icons.TRIANGLE}, override=False)

    assert VG.nodes[0].icon == Icons.CIRCLE  # kept
    assert VG.nodes[1].icon == Icons.TRIANGLE  # set


def test_set_node_icons_override_true() -> None:
    nodes = [Node(id="1", icon=Icons.CIRCLE)]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_icons(icons={"1": Icons.SQUARE}, override=True)

    assert VG.nodes[0].icon == Icons.SQUARE


def test_set_node_icons_skips_missing_value() -> None:
    nodes = [Node(id="1", properties={"label": "Person"}), Node(id="2", properties={})]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_icons(property="label", mapping={"Person": Icons.USER_SHIELD})

    assert VG.nodes[0].icon == Icons.USER_SHIELD
    assert VG.nodes[1].icon is None


def test_set_node_icons_skips_unhashable_value() -> None:
    nodes = [Node(id="1", properties={"label": ["Person"]})]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_icons(property="label", mapping={"Person": Icons.USER_SHIELD})

    assert VG.nodes[0].icon is None


def test_set_node_icons_none_provided() -> None:
    VG = VisualizationGraph(nodes=[Node(id="1")], relationships=[])

    with pytest.raises(ValueError, match="Exactly one of the arguments"):
        VG.set_node_icons()


def test_set_node_icons_field_and_property() -> None:
    VG = VisualizationGraph(nodes=[Node(id="1")], relationships=[])

    with pytest.raises(ValueError, match="Exactly one of the arguments"):
        VG.set_node_icons(field="id", property="label")


def test_set_node_icons_icons_and_field() -> None:
    VG = VisualizationGraph(nodes=[Node(id="1")], relationships=[])

    with pytest.raises(ValueError, match="Exactly one of the arguments"):
        VG.set_node_icons(icons={"1": Icons.CIRCLE}, field="id")


def test_set_node_icons_mapping_with_icons() -> None:
    VG = VisualizationGraph(nodes=[Node(id="1")], relationships=[])

    with pytest.raises(ValueError, match="`mapping` can only be combined"):
        VG.set_node_icons(icons={"1": Icons.CIRCLE}, mapping={"a": Icons.SQUARE})


def test_icon_from_svg_encodes_markup() -> None:
    uri = icon_from_svg('<svg xmlns="http://www.w3.org/2000/svg"/>')

    assert uri.startswith("data:image/svg+xml,")
    assert "<" not in uri and '"' not in uri


def test_icon_from_file_svg(tmp_path: Path) -> None:
    path = tmp_path / "icon.svg"
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')

    assert icon_from_file(path).startswith("data:image/svg+xml,")


def test_icon_from_file_png(tmp_path: Path) -> None:
    path = tmp_path / "icon.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n")

    assert icon_from_file(path).startswith("data:image/png;base64,")


def test_icon_from_file_unsupported(tmp_path: Path) -> None:
    path = tmp_path / "icon.txt"
    path.write_text("not an image")

    with pytest.raises(ValueError, match="Unsupported icon file type"):
        icon_from_file(path)


def test_icons_from_directory(tmp_path: Path) -> None:
    (tmp_path / "Person.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    (tmp_path / "Company.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    icons = icons_from_directory(tmp_path)

    assert set(icons) == {"Person", "Company"}
    assert icons["Person"].startswith("data:image/svg+xml,")
    assert icons["Company"].startswith("data:image/png;base64,")


def test_icons_from_directory_skips_unsupported_with_warning(tmp_path: Path) -> None:
    (tmp_path / "Person.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    (tmp_path / "notes.txt").write_text("not an image")

    with pytest.warns(UserWarning, match="notes.txt"):
        icons = icons_from_directory(tmp_path)

    assert set(icons) == {"Person"}


def test_icons_from_directory_skips_hidden_silently(tmp_path: Path) -> None:
    (tmp_path / "Person.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    (tmp_path / ".DS_Store").write_bytes(b"\x00\x00")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        icons = icons_from_directory(tmp_path)

    assert set(icons) == {"Person"}


def test_icons_from_directory_duplicate_name_raises(tmp_path: Path) -> None:
    (tmp_path / "Person.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    (tmp_path / "Person.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    with pytest.raises(ValueError, match="Duplicate icon name 'Person'"):
        icons_from_directory(tmp_path)


def test_icons_from_directory_missing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not exist or is not a directory"):
        icons_from_directory(tmp_path / "does-not-exist")


def test_icons_from_directory_empty(tmp_path: Path) -> None:
    assert icons_from_directory(tmp_path) == {}


def test_icons_from_directory_feeds_set_node_icons(tmp_path: Path) -> None:
    (tmp_path / "Person.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    (tmp_path / "Company.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    icons = icons_from_directory(tmp_path)

    nodes = [
        Node(id="1", properties={"label": "Person"}),
        Node(id="2", properties={"label": "Company"}),
    ]
    VG = VisualizationGraph(nodes=nodes, relationships=[])

    VG.set_node_icons(property="label", mapping=icons)

    assert VG.nodes[0].icon == icons["Person"]
    assert VG.nodes[1].icon == icons["Company"]


class _FakeResponse:
    def __init__(self, data: bytes, content_type: str) -> None:
        self._data = data
        self.headers = email.message.Message()
        self.headers["Content-Type"] = content_type

    def read(self, size: int = -1) -> bytes:
        return self._data if size < 0 else self._data[:size]

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_icon_from_url_svg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        icons_module,
        "urlopen",
        lambda request, timeout=None: _FakeResponse(b'<svg xmlns="http://www.w3.org/2000/svg"/>', "image/svg+xml"),
    )

    assert icon_from_url("https://example.com/icon.svg").startswith("data:image/svg+xml,")


def test_icon_from_url_png(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        icons_module,
        "urlopen",
        lambda request, timeout=None: _FakeResponse(b"\x89PNG\r\n\x1a\n", "image/png"),
    )

    assert icon_from_url("https://example.com/icon.png").startswith("data:image/png;base64,")


def test_icon_from_url_sends_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request: object, timeout: float | None = None) -> _FakeResponse:
        captured["request"] = request
        return _FakeResponse(b"\x89PNG\r\n\x1a\n", "image/png")

    monkeypatch.setattr(icons_module, "urlopen", fake_urlopen)
    icon_from_url("https://example.com/icon.png")

    request = captured["request"]
    assert getattr(request, "get_header")("User-agent") == "neo4j-viz"


def test_icon_from_url_data_uri_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(request: object, timeout: float | None = None) -> _FakeResponse:
        raise AssertionError("a data URI must not be fetched")

    monkeypatch.setattr(icons_module, "urlopen", fail)

    uri = "data:image/svg+xml,%3Csvg%2F%3E"
    assert icon_from_url(uri) == uri


def test_icon_from_url_rejects_non_image(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        icons_module,
        "urlopen",
        lambda request, timeout=None: _FakeResponse(b"<html>Not found</html>", "text/html"),
    )

    with pytest.raises(ValueError, match="not a supported image type"):
        icon_from_url("https://example.com/missing.svg")


def test_icon_from_url_rejects_too_large(monkeypatch: pytest.MonkeyPatch) -> None:
    oversized = b"x" * (icons_module._MAX_ICON_BYTES + 1)
    monkeypatch.setattr(
        icons_module,
        "urlopen",
        lambda request, timeout=None: _FakeResponse(oversized, "image/png"),
    )

    with pytest.raises(ValueError, match="larger than the maximum"):
        icon_from_url("https://example.com/huge.png")


def test_icon_from_url_rejects_non_http_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(request: object, timeout: float | None = None) -> _FakeResponse:
        raise AssertionError("should not fetch")

    monkeypatch.setattr(icons_module, "urlopen", fail)

    with pytest.raises(ValueError, match="Unsupported icon URL scheme"):
        icon_from_url("file:///tmp/icon.svg")
    with pytest.raises(ValueError, match="Unsupported icon URL scheme"):
        icon_from_url("person")


def test_icon_from_url_propagates_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request: object, timeout: float | None = None) -> _FakeResponse:
        raise HTTPError("https://example.com/missing.svg", 404, "Not Found", email.message.Message(), None)

    monkeypatch.setattr(icons_module, "urlopen", fake_urlopen)

    with pytest.raises(HTTPError):
        icon_from_url("https://example.com/missing.svg")


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def test_icon_catalog_matches_js_registry() -> None:
    registry_path = Path(__file__).parents[2] / "js-applet" / "src" / "icon-registry.ts"
    assert registry_path.exists(), f"missing {registry_path}; run `yarn generate:icons` in js-applet"

    registry_keys = set(
        re.findall(r'^\s{2}([A-Za-z0-9_]+):\s*(?:"data:|$)', registry_path.read_text(), flags=re.MULTILINE)
    )
    enum_names = {str(icon.value) for icon in Icons}

    assert {_normalize(key) for key in registry_keys} == {_normalize(name) for name in enum_names}
