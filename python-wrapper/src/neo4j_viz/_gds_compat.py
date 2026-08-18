from __future__ import annotations

import importlib
import re
from typing import Any, ContextManager, cast

from graphdatascience import Graph, GraphDataScience
from graphdatascience.procedure_surface.api.centrality.degree_endpoints import DegreeEndpoints
from graphdatascience.procedure_surface.arrow.catalog.catalog_arrow_endpoints import (
    CatalogArrowEndpoints,
)
from graphdatascience.procedure_surface.cypher.catalog.catalog_cypher_endpoints import (
    CatalogCypherEndpoints,
)
from graphdatascience.session import AuraGraphDataScience
from graphdatascience.version import __version__ as _gds_version

CatalogEndpoints = CatalogArrowEndpoints | CatalogCypherEndpoints
_GdsClient = GraphDataScience | AuraGraphDataScience


def _parse_major(version: str) -> int:
    match = re.match(r"\s*(\d+)", version)
    return int(match.group(1)) if match else 0


IS_GDS_2: bool = _parse_major(_gds_version) >= 2

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


def _catalog(gds: _GdsClient) -> CatalogEndpoints:
    """Return the graph catalog endpoints for either client version.

    In GDS v2 the catalog lives at ``gds.graph``; in v1 (1.22) the v2-compatible surface
    is reached via ``gds.v2.graph``. The client is cast to ``Any`` for the attribute access
    so the same code type-checks under either install (the two versions expose the catalog
    under different attributes); the return type stays the shared concrete catalog union,
    so callers are type-checked against whichever version is installed.
    """
    if IS_GDS_2:
        return cast("CatalogEndpoints", cast(Any, gds).graph)
    return cast("CatalogEndpoints", cast(Any, gds).v2.graph)


def _degree_centrality(gds: _GdsClient) -> DegreeEndpoints:
    """Return the degree centrality endpoints for either client version."""
    if IS_GDS_2:
        return cast("DegreeEndpoints", cast(Any, gds).degree_centrality)
    return cast("DegreeEndpoints", cast(Any, gds).v2.degree_centrality)


def _project_native(
    gds: _GdsClient, graph_name: str, node_labels: list[str], relationship_types: list[str]
) -> ContextManager[Graph]:
    """Native (label/type filter) projection for either client version.

    In GDS v2 this is ``graph.project.native(...)`` (a property); in v1 it is the callable
    ``graph.project(...)``. The dispatch differs, so the catalog is cast to ``Any`` here —
    but the helper signature stays concrete, so wrong call-site arguments (e.g. passing
    ``"*"`` instead of ``["*"]``) are still caught by mypy. The result is a context manager
    yielding the projected graph in both versions.
    """
    if IS_GDS_2:
        return cast(
            "ContextManager[Graph]",
            cast(Any, _catalog(gds)).project.native(graph_name, node_labels, relationship_types),
        )
    return cast("ContextManager[Graph]", cast(Any, _catalog(gds)).project(graph_name, node_labels, relationship_types))


def _project_cypher(gds: _GdsClient, graph_name: str, query: str) -> ContextManager[Graph]:
    """Cypher projection for either client version.

    In GDS v2 this is ``graph.project.cypher(...)`` (a property); in v1 it is the callable
    ``graph.project(name, query)``.
    """
    if IS_GDS_2:
        return cast("ContextManager[Graph]", cast(Any, _catalog(gds)).project.cypher(graph_name, query))
    return cast("ContextManager[Graph]", cast(Any, _catalog(gds)).project(graph_name, query))
