from collections.abc import Iterable, Sequence
from enum import Enum
from math import floor
from typing import Any, Union

import enum_tools
from pydantic_extra_types.color import Color, ColorType

from .node_size import RealNumber

ColorsType = Union[dict[Any, ColorType], Iterable[ColorType]]


def to_color(color: ColorType) -> Color:
    return color if isinstance(color, Color) else Color(color)


def to_hex(color: ColorType) -> str:
    return to_color(color).as_hex(format="long")


def _rgba(color: Color) -> tuple[int, int, int, float]:
    rgba = color.as_rgb_tuple()
    if len(rgba) == 3:
        return rgba[0], rgba[1], rgba[2], 1.0
    return rgba[0], rgba[1], rgba[2], rgba[3]


def interpolate_gradient(colors: Sequence[ColorType], t: RealNumber) -> Color:
    """
    Interpolate a color along a gradient of color stops.

    Parameters
    ----------
    colors:
        The color stops of the gradient, from the color of the lowest value to the color of the highest value.
    t:
        The position along the gradient, between 0 (the first color stop) and 1 (the last color stop).

    Raises
    ------
    ValueError
        If `colors` is empty.
    """
    resolved = [to_color(color) for color in colors]
    if not resolved:
        raise ValueError("At least one color is needed to interpolate a gradient")

    if len(resolved) == 1:
        return resolved[0]

    if not 0 <= t <= 1:
        t = min(max(t, 0.0), 1.0)

    scaled = t * (len(resolved) - 1)
    lower = floor(scaled)
    if lower >= len(resolved) - 1:
        return resolved[-1]

    r1, g1, b1, a1 = _rgba(resolved[lower])
    r2, g2, b2, a2 = _rgba(resolved[lower + 1])
    fraction = scaled - lower

    return Color(
        (
            round(r1 + fraction * (r2 - r1)),
            round(g1 + fraction * (g2 - g1)),
            round(b1 + fraction * (b2 - b1)),
            a1 + fraction * (a2 - a1),
        )
    )


@enum_tools.documentation.document_enum
class ColorSpace(str, Enum):
    """
    Describes the type of color space used by a color palette.
    """

    DISCRETE = "discrete"
    """
    This category describes a color palette that is a collection of different colors that are not necessarily related to
    each other. Discrete color spaces are suitable for categorical data, where each unique category is represented by a
    different color.
    """
    CONTINUOUS = "continuous"
    """
    This category describes a color palette that is a range/gradient of colors between two or more colors. Continuous
    color spaces are suitable for continuous data (typically floats), where values can change smoothly.
    """


# Comes from https://neo4j.design/40a8cff71/p/5639c0-color/t/page-5639c0-79109681-33
NEO4J_COLORS_DISCRETE = [
    "#FFDF81",
    "#C990C0",
    "#F79767",
    "#56C7E4",
    "#F16767",
    "#D8C7AE",
    "#8DCC93",
    "#ECB4C9",
    "#4D8DDA",
    "#FFC354",
    "#DA7294",
    "#579380",
]
_NEO4J_COLORS_CONTINUOUS_BASE = ["#FFDF81", "#C990C0"]
NEO4J_COLORS_CONTINUOUS = [
    (255, 223, 129),
    (255, 223, 129),
    (255, 222, 129),
    (254, 222, 130),
    (254, 222, 130),
    (254, 221, 130),
    (254, 221, 130),
    (254, 221, 131),
    (253, 221, 131),
    (253, 220, 131),
    (253, 220, 131),
    (253, 220, 132),
    (252, 219, 132),
    (252, 219, 132),
    (252, 219, 132),
    (252, 218, 133),
    (252, 218, 133),
    (251, 218, 133),
    (251, 217, 133),
    (251, 217, 134),
    (251, 217, 134),
    (251, 216, 134),
    (250, 216, 134),
    (250, 216, 135),
    (250, 216, 135),
    (250, 215, 135),
    (249, 215, 135),
    (249, 215, 136),
    (249, 214, 136),
    (249, 214, 136),
    (249, 214, 136),
    (248, 213, 137),
    (248, 213, 137),
    (248, 213, 137),
    (248, 212, 137),
    (248, 212, 138),
    (247, 212, 138),
    (247, 212, 138),
    (247, 211, 138),
    (247, 211, 139),
    (247, 211, 139),
    (246, 210, 139),
    (246, 210, 139),
    (246, 210, 140),
    (246, 209, 140),
    (245, 209, 140),
    (245, 209, 140),
    (245, 208, 141),
    (245, 208, 141),
    (245, 208, 141),
    (244, 208, 141),
    (244, 207, 142),
    (244, 207, 142),
    (244, 207, 142),
    (244, 206, 142),
    (243, 206, 143),
    (243, 206, 143),
    (243, 205, 143),
    (243, 205, 143),
    (243, 205, 144),
    (242, 204, 144),
    (242, 204, 144),
    (242, 204, 144),
    (242, 203, 145),
    (241, 203, 145),
    (241, 203, 145),
    (241, 203, 145),
    (241, 202, 146),
    (241, 202, 146),
    (240, 202, 146),
    (240, 201, 146),
    (240, 201, 147),
    (240, 201, 147),
    (240, 200, 147),
    (239, 200, 147),
    (239, 200, 148),
    (239, 199, 148),
    (239, 199, 148),
    (238, 199, 148),
    (238, 199, 149),
    (238, 198, 149),
    (238, 198, 149),
    (238, 198, 149),
    (237, 197, 150),
    (237, 197, 150),
    (237, 197, 150),
    (237, 196, 150),
    (237, 196, 150),
    (236, 196, 151),
    (236, 195, 151),
    (236, 195, 151),
    (236, 195, 151),
    (236, 194, 152),
    (235, 194, 152),
    (235, 194, 152),
    (235, 194, 152),
    (235, 193, 153),
    (234, 193, 153),
    (234, 193, 153),
    (234, 192, 153),
    (234, 192, 154),
    (234, 192, 154),
    (233, 191, 154),
    (233, 191, 154),
    (233, 191, 155),
    (233, 190, 155),
    (233, 190, 155),
    (232, 190, 155),
    (232, 190, 156),
    (232, 189, 156),
    (232, 189, 156),
    (231, 189, 156),
    (231, 188, 157),
    (231, 188, 157),
    (231, 188, 157),
    (231, 187, 157),
    (230, 187, 158),
    (230, 187, 158),
    (230, 186, 158),
    (230, 186, 158),
    (230, 186, 159),
    (229, 186, 159),
    (229, 185, 159),
    (229, 185, 159),
    (229, 185, 160),
    (229, 184, 160),
    (228, 184, 160),
    (228, 184, 160),
    (228, 183, 161),
    (228, 183, 161),
    (227, 183, 161),
    (227, 182, 161),
    (227, 182, 162),
    (227, 182, 162),
    (227, 181, 162),
    (226, 181, 162),
    (226, 181, 163),
    (226, 181, 163),
    (226, 180, 163),
    (226, 180, 163),
    (225, 180, 164),
    (225, 179, 164),
    (225, 179, 164),
    (225, 179, 164),
    (225, 178, 165),
    (224, 178, 165),
    (224, 178, 165),
    (224, 177, 165),
    (224, 177, 166),
    (223, 177, 166),
    (223, 177, 166),
    (223, 176, 166),
    (223, 176, 167),
    (223, 176, 167),
    (222, 175, 167),
    (222, 175, 167),
    (222, 175, 168),
    (222, 174, 168),
    (222, 174, 168),
    (221, 174, 168),
    (221, 173, 169),
    (221, 173, 169),
    (221, 173, 169),
    (220, 173, 169),
    (220, 172, 170),
    (220, 172, 170),
    (220, 172, 170),
    (220, 171, 170),
    (219, 171, 171),
    (219, 171, 171),
    (219, 170, 171),
    (219, 170, 171),
    (219, 170, 171),
    (218, 169, 172),
    (218, 169, 172),
    (218, 169, 172),
    (218, 168, 172),
    (218, 168, 173),
    (217, 168, 173),
    (217, 168, 173),
    (217, 167, 173),
    (217, 167, 174),
    (216, 167, 174),
    (216, 166, 174),
    (216, 166, 174),
    (216, 166, 175),
    (216, 165, 175),
    (215, 165, 175),
    (215, 165, 175),
    (215, 164, 176),
    (215, 164, 176),
    (215, 164, 176),
    (214, 164, 176),
    (214, 163, 177),
    (214, 163, 177),
    (214, 163, 177),
    (213, 162, 177),
    (213, 162, 178),
    (213, 162, 178),
    (213, 161, 178),
    (213, 161, 178),
    (212, 161, 179),
    (212, 160, 179),
    (212, 160, 179),
    (212, 160, 179),
    (212, 159, 180),
    (211, 159, 180),
    (211, 159, 180),
    (211, 159, 180),
    (211, 158, 181),
    (211, 158, 181),
    (210, 158, 181),
    (210, 157, 181),
    (210, 157, 182),
    (210, 157, 182),
    (209, 156, 182),
    (209, 156, 182),
    (209, 156, 183),
    (209, 155, 183),
    (209, 155, 183),
    (208, 155, 183),
    (208, 155, 184),
    (208, 154, 184),
    (208, 154, 184),
    (208, 154, 184),
    (207, 153, 185),
    (207, 153, 185),
    (207, 153, 185),
    (207, 152, 185),
    (207, 152, 186),
    (206, 152, 186),
    (206, 151, 186),
    (206, 151, 186),
    (206, 151, 187),
    (205, 151, 187),
    (205, 150, 187),
    (205, 150, 187),
    (205, 150, 188),
    (205, 149, 188),
    (204, 149, 188),
    (204, 149, 188),
    (204, 148, 189),
    (204, 148, 189),
    (204, 148, 189),
    (203, 147, 189),
    (203, 147, 190),
    (203, 147, 190),
    (203, 146, 190),
    (202, 146, 190),
    (202, 146, 191),
    (202, 146, 191),
    (202, 145, 191),
    (202, 145, 191),
    (201, 145, 192),
    (201, 144, 192),
    (201, 144, 192),
]
