import contextlib
import warnings
from collections.abc import Iterator

import pytest

from neo4j_viz._validation import check_dangling_relationships
from neo4j_viz.node import Node
from neo4j_viz.relationship import Relationship


@contextlib.contextmanager
def assert_no_warning() -> Iterator[None]:
    """Turn any emitted warning into an error, so the test fails if one is raised."""
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        yield


def test_no_dangling_is_silent() -> None:
    nodes = [Node(id="a"), Node(id="b")]
    rels = [Relationship(id="r1", source="a", target="b")]
    with assert_no_warning():
        check_dangling_relationships(nodes, rels)  # must not warn or raise


def test_reports_only_the_missing_target() -> None:
    nodes = [Node(id="a"), Node(id="b")]
    rels = [Relationship(id="r1", source="a", target="missing")]

    with pytest.warns(UserWarning) as record:
        check_dangling_relationships(nodes, rels)

    msg = str(record[0].message)
    assert "1 relationship(s) reference node ids that are not in the graph" in msg
    assert "relationship 'r1' (source='a', target='missing') -> missing ['missing']" in msg
    # the present endpoint must not be reported as missing
    assert "'a'" not in msg.split("missing [", 1)[1]


def test_reports_only_the_missing_source() -> None:
    nodes = [Node(id="a"), Node(id="b")]
    rels = [Relationship(id="r1", source="ghost", target="b")]

    with pytest.warns(UserWarning) as record:
        check_dangling_relationships(nodes, rels)

    assert "-> missing ['ghost']" in str(record[0].message)


def test_reports_both_missing_endpoints_in_order() -> None:
    nodes = [Node(id="a")]
    rels = [Relationship(id="r1", source="x", target="y")]

    with pytest.warns(UserWarning) as record:
        check_dangling_relationships(nodes, rels)

    # source is reported before target
    assert "-> missing ['x', 'y']" in str(record[0].message)


def test_mixed_id_types_match() -> None:
    # Node(id=1) (int) and Relationship(source="1") (str) refer to the same node -> not dangling
    nodes = [Node(id=1), Node(id=2)]
    rels = [Relationship(id="r1", source="1", target=2)]
    with assert_no_warning():
        check_dangling_relationships(nodes, rels)


def test_mixed_id_types_partial_miss() -> None:
    nodes = [Node(id=1)]
    rels = [Relationship(id="r1", source="1", target="x")]

    with pytest.warns(UserWarning) as record:
        check_dangling_relationships(nodes, rels)

    # source "1" matches Node(id=1); only the genuinely missing target is reported
    assert "-> missing ['x']" in str(record[0].message)


def test_error_mode_reports_missing_ids() -> None:
    nodes = [Node(id="a")]
    rels = [Relationship(id="r1", source="a", target="b")]

    with pytest.raises(ValueError) as excinfo:
        check_dangling_relationships(nodes, rels, on_dangling="error")

    msg = str(excinfo.value)
    assert "1 relationship(s) reference node ids that are not in the graph" in msg
    assert "relationship 'r1' (source='a', target='b') -> missing ['b']" in msg


def test_none_mode_is_silent_even_with_dangling() -> None:
    nodes = [Node(id="a")]
    rels = [Relationship(id="r1", source="a", target="b")]
    with assert_no_warning():
        check_dangling_relationships(nodes, rels, on_dangling="none")  # must not warn or raise


def test_multiple_dangling_are_all_counted_and_capped() -> None:
    nodes = [Node(id="n")]
    rels = [Relationship(id=f"r{i}", source="n", target=f"m{i}") for i in range(7)]

    with pytest.warns(UserWarning) as record:
        check_dangling_relationships(nodes, rels)

    msg = str(record[0].message)
    assert "7 relationship(s) reference node ids that are not in the graph" in msg
    # first 5 are listed, the rest summarized
    assert "-> missing ['m0']" in msg
    assert "-> missing ['m4']" in msg
    assert "'m5'" not in msg and "'m6'" not in msg
    assert "... and 2 more" in msg
