from collections.abc import Hashable
from enum import StrEnum
from math import log1p, sqrt
from typing import TypeVar, Union

RealNumber = Union[int, float]
SizeKey = TypeVar("SizeKey", bound=Hashable)


class NodeSizing(StrEnum):
    """
    Describes how a node value maps to a node radius when the values are scaled to a radius range.
    """

    RADIUS = "radius"
    """
    The radius grows linearly with the value, so the area grows with the square of the value.
    """
    AREA = "area"
    """
    The area grows linearly with the value, so the radius grows with the square root of the value.
    This matches how Bloom sizes nodes, and it is the default.
    """
    LOG = "log"
    """
    The radius grows with the logarithm of the value, which compresses skewed value distributions such as
    degree or PageRank. Zero values are supported, since the logarithm is taken of the value plus one.
    """


def verify_radii(node_radius_min_max: tuple[RealNumber, RealNumber]) -> None:
    if not isinstance(node_radius_min_max, tuple):
        raise ValueError(f"`node_radius_min_max` must be a tuple of two values, but was {node_radius_min_max}")

    if len(node_radius_min_max) != 2:
        raise ValueError(f"`node_radius_min_max` must be a tuple of two values, but was {node_radius_min_max}")

    min_size, max_size = node_radius_min_max
    if not isinstance(min_size, (int, float)):
        raise ValueError(f"Minimum node size must be a real number, but was of type {type(min_size)}")

    if not isinstance(max_size, (int, float)):
        raise ValueError(f"Maximum node size must be a real number, but was of type {type(max_size)}")

    if min_size < 0:
        raise ValueError(f"Minimum node size must be non-negative, but was {min_size}")

    if max_size < 0:
        raise ValueError(f"Maximum node size must be non-negative, but was {max_size}")

    if min_size > max_size:
        raise ValueError(
            f"Minimum node size must be less than or equal to maximum node size, but was {min_size} > {max_size}"
        )


def scale_sizes(
    values: dict[SizeKey, RealNumber],
    node_radius_min_max: tuple[RealNumber, RealNumber],
    sizing: NodeSizing | str = NodeSizing.AREA,
) -> dict[SizeKey, RealNumber]:
    """
    Scale the given values to the given radius range, according to the sizing mode.

    Parameters
    ----------
    values:
        The values to scale, keyed by node ID.
    node_radius_min_max:
        Minimum and maximum radius to scale the values to. Expected to be validated by `verify_radii`.
    sizing:
        How the values map to radii. See `NodeSizing`.

    Raises
    ------
    ValueError
        If `sizing` is not a `NodeSizing` value.
    """
    if not values:
        return {}

    sizing = NodeSizing(sizing)

    min_radius, max_radius = node_radius_min_max

    if sizing == NodeSizing.LOG:
        # log1p keeps zero values, such as a degree of zero, finite
        values = {id: log1p(value) for id, value in values.items()}

    min_value = min(values.values())
    max_value = max(values.values())
    value_range = float(max_value - min_value)

    if abs(value_range) < 1e-6:
        # All values are equal, so fall back to the middle of the range to keep the nodes visible
        if sizing == NodeSizing.AREA:
            middle = sqrt((min_radius**2 + max_radius**2) / 2.0)
        else:
            middle = min_radius + (max_radius - min_radius) / 2.0
        return {id: middle for id in values}

    if sizing == NodeSizing.AREA:
        # Interpolate the squared radius, so that the area grows linearly with the value
        return {
            id: sqrt(min_radius**2 + (max_radius**2 - min_radius**2) * ((value - min_value) / value_range))
            for id, value in values.items()
        }

    return {
        id: min_radius + (max_radius - min_radius) * ((value - min_value) / value_range) for id, value in values.items()
    }
