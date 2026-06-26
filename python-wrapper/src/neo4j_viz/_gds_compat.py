"""Compatibility shims for the Neo4j GDS Python client.

Supports both the GDS 1.22 transitional API (graph operations exposed under the
``gds.v2.*`` namespace, graph objects of type ``GraphV2``) and the GDS 2.0 API
(the v2 endpoints became the default, so they live directly under ``gds.*`` and
the graph class was renamed from ``GraphV2`` to ``Graph``).

The two APIs are selected by the installed client's major version, exposed via
``graphdatascience.version.__version__``: major ``>= 2`` means the v2 endpoints
are the default.
"""

from __future__ import annotations

import importlib
import re
from typing import Any

from graphdatascience.version import __version__ as _gds_version


def _parse_major(version: str) -> int:
    match = re.match(r"\s*(\d+)", version)
    return int(match.group(1)) if match else 0


# In GDS 2.0 the (formerly ``v2``) endpoints became the default: graph operations moved
# from ``gds.v2.*`` to ``gds.*`` and ``GraphV2`` was renamed to ``Graph``.
IS_GDS_2: bool = _parse_major(_gds_version) >= 2

# The native graph class for the installed client version. Resolved dynamically (typed
# ``Any``) because its import path differs between versions and only one path exists at a time.
# ``_GRAPH_TYPES`` is the full set of graph objects accepted as input to ``from_gds``: on the
# 1.22 transitional client we also accept the legacy v1 ``Graph`` (which is then converted).
if IS_GDS_2:
    GdsGraph: Any = importlib.import_module("graphdatascience.graph").Graph
    _GRAPH_TYPES: tuple[type, ...] = (GdsGraph,)
else:
    GdsGraph = importlib.import_module("graphdatascience.graph.v2").GraphV2
    _GRAPH_TYPES = (GdsGraph, importlib.import_module("graphdatascience").Graph)


def _check_graph_type(G: Any) -> None:
    """Raise ``TypeError`` unless ``G`` is a graph object accepted by the installed client."""
    if not isinstance(G, _GRAPH_TYPES):
        accepted = " or ".join(t.__name__ for t in _GRAPH_TYPES)
        raise TypeError(f"`G` must be a GDS graph object ({accepted}), but got {type(G).__name__}")


def _catalog(gds: Any) -> Any:
    """Return the graph catalog endpoints for either client version."""
    return gds.graph if IS_GDS_2 else gds.v2.graph


def _degree_centrality(gds: Any) -> Any:
    """Return the degree centrality endpoints for either client version."""
    return gds.degree_centrality if IS_GDS_2 else gds.v2.degree_centrality
