import pytest

from neo4j_viz import CaptionAlignment, Node


def test_nodes_with_all_options() -> None:
    node = Node(
        id="4:d09f48a4-5fca-421d-921d-a30a896c604d:0",
        caption="Person",
        caption_align=CaptionAlignment.TOP,
        caption_size=1,
        color="#FF0000",
        size=10,
        pinned=True,
        x=1,
        y=10,
    )

    assert node.to_dict() == {
        "id": "4:d09f48a4-5fca-421d-921d-a30a896c604d:0",
        "caption": "Person",
        "captionAlign": "top",
        "captionSize": 1,
        "color": "#ff0000",
        "size": 10,
        "pinned": True,
        "x": 1,
        "y": 10,
        "properties": {},
    }


def test_nodes_minimal_node() -> None:
    node = Node(
        id="1",
    )

    assert node.to_dict() == {
        "id": "1",
        "properties": {},
    }


def test_node_with_float_size() -> None:
    node = Node(
        id="1",
        size=10.2,
    )

    assert node.to_dict() == {
        "id": "1",
        "size": 10.2,
        "properties": {},
    }


def test_node_with_additional_fields() -> None:
    node = Node(
        id="1",
        componentId=2,
    )

    assert node.to_dict() == {
        "id": "1",
        "componentId": 2,
        "properties": {},
    }


@pytest.mark.parametrize("alias", ["id", "nodeId", "node_id"])
def test_id_aliases(alias: str) -> None:
    node = Node(**{alias: 1})

    assert node.to_dict() == {
        "id": "1",
        "properties": {},
    }


def test_node_validation() -> None:
    with pytest.raises(ValueError, match="Input should be a valid integer, unable to parse string as an integer"):
        Node(id="1", x="not a number")
