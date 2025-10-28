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


def test_node_with_properties() -> None:
    node = Node(
        id="1",
        properties=dict(componentId=2),
    )

    assert node.to_dict() == {
        "id": "1",
        "properties": {"componentId": 2},
    }


@pytest.mark.parametrize("alias", ["id", "nodeId", "node_id", "NODEID", "nodeid"])
def test_id_aliases(alias: str) -> None:
    node = Node(**{alias: 1})

    assert node.to_dict() == {
        "id": "1",
        "properties": {},
    }


def test_node_validation() -> None:
    with pytest.raises(ValueError, match="Input should be a valid integer, unable to parse string as an integer"):
        Node(id="1", x="not a number")


def test_node_casing() -> None:
    node = Node(
        ID="4:d09f48a4-5fca-421d-921d-a30a896c604d:0",
        caption="Person",
        captionAlign=CaptionAlignment.TOP,
        CAPTION_SIZE=1,
    )

    assert node.id == "4:d09f48a4-5fca-421d-921d-a30a896c604d:0"
    assert node.caption == "Person"
    assert node.caption_align == CaptionAlignment.TOP
    assert node.caption_size == 1


def test_all_validation_aliases() -> None:
    all_aliases = Node.basic_fields_validation_aliases()
    assert "id" in all_aliases
    assert "ID" in all_aliases
    assert "NODE_ID" in all_aliases
