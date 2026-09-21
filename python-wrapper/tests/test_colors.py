import pytest
from pydantic_extra_types.color import Color

from neo4j_viz.colors import to_color, to_hex


class TestToColor:
    def test_passes_through_color_instances(self) -> None:
        color = Color("red")

        assert to_color(color) is color

    def test_casts_hex_string(self) -> None:
        assert to_color("#ff0000") == Color((255, 0, 0))

    def test_casts_named_color(self) -> None:
        assert to_color("red") == Color((255, 0, 0))

    def test_casts_rgb_tuple(self) -> None:
        assert to_color((255, 0, 0)) == Color((255, 0, 0))

    def test_rejects_invalid_color(self) -> None:
        with pytest.raises(ValueError, match="not a valid color"):
            to_color("not-a-color")


class TestToHex:
    @pytest.mark.parametrize(
        ("color", "expected"),
        [
            ("#ffffff", "#ffffff"),
            ("#fff", "#ffffff"),
            ("red", "#ff0000"),
            ((255, 0, 0), "#ff0000"),
            ((255, 0, 0, 0.5), "#ff000080"),
            (Color("red"), "#ff0000"),
        ],
    )
    def test_normalizes_to_long_hex(self, color: object, expected: str) -> None:
        assert to_hex(color) == expected  # type: ignore[arg-type]
