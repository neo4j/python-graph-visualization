import pytest
from pydantic_extra_types.color import Color

from neo4j_viz.colors import interpolate_gradient, to_color, to_hex


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


class TestInterpolateGradient:
    @pytest.mark.parametrize("t", [0.0, 1.0])
    def test_endpoints_are_the_exact_stops(self, t: float) -> None:
        gradient = ["#E0E0E0", "#000000"]

        assert interpolate_gradient(gradient, t) == Color(gradient[round(t)])

    def test_interpolates_between_two_stops(self) -> None:
        gradient = ["#E0E0E0", "#000000"]

        assert interpolate_gradient(gradient, 0.25) == Color((168, 168, 168))
        assert interpolate_gradient(gradient, 0.5) == Color((112, 112, 112))
        assert interpolate_gradient(gradient, 0.75) == Color((56, 56, 56))

    def test_interpolates_across_multiple_stops(self) -> None:
        gradient = ["#000000", "#808080", "#FFFFFF"]

        assert interpolate_gradient(gradient, 0.25) == Color((64, 64, 64))
        assert interpolate_gradient(gradient, 0.5) == Color((128, 128, 128))
        assert interpolate_gradient(gradient, 0.75) == Color((192, 192, 192))

    def test_interpolates_alpha(self) -> None:
        gradient = [(255, 0, 0, 0.0), (0, 0, 255, 1.0)]

        assert to_hex(interpolate_gradient(gradient, 0.5)) == "#80008080"

    def test_single_stop_is_constant(self) -> None:
        assert interpolate_gradient(["#01ABCD"], 0.3) == Color("#01abcd")

    def test_rejects_out_of_range_positions(self) -> None:
        gradient = ["#E0E0E0", "#000000"]

        with pytest.raises(ValueError, match="The gradient position must be between 0 and 1"):
            interpolate_gradient(gradient, -1)

        with pytest.raises(ValueError, match="The gradient position must be between 0 and 1"):
            interpolate_gradient(gradient, 1.5)

    def test_rejects_empty_gradient(self) -> None:
        with pytest.raises(ValueError, match="At least one color is needed to interpolate a gradient"):
            interpolate_gradient([], 0.5)
