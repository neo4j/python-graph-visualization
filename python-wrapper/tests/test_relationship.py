import pytest

from neo4j_viz import CaptionAlignment
from neo4j_viz.relationship import Relationship


def test_rels_with_all_options() -> None:
    rel = Relationship(
        id="1",
        source="2",
        target="3",
        caption="BUYS",
        caption_align=CaptionAlignment.TOP,
        caption_size=12,
        color="#FF0000",
    )

    assert rel.to_dict() == {
        "id": "1",
        "from": "2",
        "to": "3",
        "caption": "BUYS",
        "captionAlign": "top",
        "captionSize": 12,
        "color": "#ff0000",
        "properties": {},
    }


def test_rels_minimal_rel() -> None:
    rel = Relationship(
        source="1",
        target="2",
    )

    rel_dict = rel.to_dict()

    assert {"id", "from", "to", "properties"} == set(rel_dict.keys())
    assert rel_dict["from"] == "1"
    assert rel_dict["to"] == "2"


def test_rels_additional_fields() -> None:
    rel = Relationship(
        source="1",
        target="2",
        properties=dict(componentId=2),
    )

    rel_dict = rel.to_dict()
    assert {"id", "from", "to", "properties"} == set(rel_dict.keys())
    assert rel.properties["componentId"] == 2


@pytest.mark.parametrize(
    "src_alias",
    ["source", "sourceNodeId", "source_node_id", "from", "SOURCE", "SOURCE_NODE_ID", "SOURCENODEID", "FROM"],
)
def test_src_aliases(src_alias: str) -> None:
    rel = Relationship(
        **{
            src_alias: "1",
            "to": "2",
        }
    )

    rel_dict = rel.to_dict()

    assert {"id", "from", "to", "properties"} == set(rel_dict.keys())
    assert rel_dict["from"] == "1"
    assert rel_dict["to"] == "2"


@pytest.mark.parametrize(
    "trg_alias", ["target", "targetNodeId", "target_node_id", "to", "TARGET", "TARGET_NODE_ID", "TARGETNODEID", "TO"]
)
def test_trg_aliases(trg_alias: str) -> None:
    rel = Relationship(
        **{
            "from": "1",
            trg_alias: "2",
        }
    )

    rel_dict = rel.to_dict()

    assert {"id", "from", "to", "properties"} == set(rel_dict.keys())
    assert rel_dict["from"] == "1"
    assert rel_dict["to"] == "2"


def test_rel_casing() -> None:
    rel = Relationship(
        ID="1",
        source="2",
        target="3",
        captionAlign=CaptionAlignment.TOP,
        CAPTION_SIZE=12,
    )

    assert rel.id == "1"
    assert rel.caption_align == CaptionAlignment.TOP
    assert rel.caption_size == 12


def test_all_validation_aliases() -> None:
    all_aliases = Relationship.basic_fields_validation_aliases()
    assert "SOURCE_NODE_ID" in all_aliases
    assert "targetNodeId" in all_aliases
    assert "source_node_id" in all_aliases
