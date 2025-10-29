import re
import uuid
from typing import Any, Optional

from pydantic import BaseModel, ValidationError

from neo4j_viz import Node, Relationship, VisualizationGraph
from neo4j_viz.colors import NEO4J_COLORS_DISCRETE, ColorSpace


def _parse_value(value_str: str) -> Any:
    value_str = value_str.strip()
    if not value_str:
        return None

    # Parse map
    if value_str.startswith("{") and value_str.endswith("}"):
        inner = value_str[1:-1].strip()
        result = {}
        depth = 0
        in_string = None
        start_idx = 0
        for i, ch in enumerate(inner):
            if in_string is None:
                if ch in ["'", '"']:
                    in_string = ch
                elif ch in ["{", "["]:
                    depth += 1
                elif ch in ["}", "]"]:
                    depth -= 1
                elif ch == "," and depth == 0:
                    segment = inner[start_idx:i].strip()
                    if ":" not in segment:
                        return None
                    k, v = segment.split(":", 1)
                    k = k.strip().strip("'\"")
                    result[k] = _parse_value(v)
                    start_idx = i + 1
            else:
                if ch == in_string:
                    in_string = None

        if inner[start_idx:]:
            segment = inner[start_idx:].strip()
            if ":" not in segment:
                return None
            k, v = segment.split(":", 1)
            k = k.strip().strip("'\"")
            result[k] = _parse_value(v)

        return result

    # Parse list
    if value_str.startswith("[") and value_str.endswith("]"):
        inner = value_str[1:-1].strip()
        items = []
        depth = 0
        in_string = None
        start_idx = 0
        for i, ch in enumerate(inner):
            if in_string is None:
                if ch in ["'", '"']:
                    in_string = ch
                elif ch in ["{", "["]:
                    depth += 1
                elif ch in ["}", "]"]:
                    depth -= 1
                elif ch == "," and depth == 0:
                    items.append(_parse_value(inner[start_idx:i]))
                    start_idx = i + 1
            else:
                if ch == in_string:
                    in_string = None

        if inner[start_idx:]:
            items.append(_parse_value(inner[start_idx:]))

        return items

    # Parse boolean, float, int, or string
    if re.match(r"^-?\d+$", value_str):
        return int(value_str)
    if re.match(r"^-?\d+\.\d+$", value_str):
        return float(value_str)
    if value_str.lower() == "true":
        return True
    if value_str.lower() == "false":
        return False
    if value_str.lower() == "null":
        return None

    return value_str.strip("'\"")


def _parse_prop_str(query: str, prop_str: str, prop_start: int) -> dict[str, Any]:
    props: dict[str, Any] = {}
    depth = 0
    in_string = None
    start_idx = 0
    for i, ch in enumerate(prop_str):
        if in_string is None:
            if ch in ["'", '"']:
                in_string = ch
            elif ch in ["{", "["]:
                depth += 1
            elif ch in ["}", "]"]:
                depth -= 1
            elif ch == "," and depth == 0:
                pair = prop_str[start_idx:i].strip()
                if ":" not in pair:
                    snippet = _get_snippet(query, prop_start + start_idx)
                    raise ValueError(f"Property syntax error near: `{snippet}`.")
                k, v = pair.split(":", 1)
                k = k.strip().strip("'\"")

                props[k] = _parse_value(v)

                start_idx = i + 1
        else:
            if ch == in_string:
                in_string = None

    if prop_str[start_idx:]:
        pair = prop_str[start_idx:].strip()
        if ":" not in pair:
            snippet = _get_snippet(query, prop_start + start_idx)
            raise ValueError(f"Property syntax error near: `{snippet}`.")
        k, v = pair.split(":", 1)
        k = k.strip().strip("'\"")

        props[k] = _parse_value(v)

    return props


def _parse_labels_and_props(query: str, s: str) -> tuple[Optional[str], dict[str, Any]]:
    prop_match = re.search(r"\{(.*)\}", s)
    prop_str = ""
    if prop_match:
        prop_str = prop_match.group(1)
        prop_start = query.index(prop_str, query.index(s))
        s = s[: prop_match.start()].strip()
    alias_labels = re.split(r"[:&]", s)
    raw_alias = alias_labels[0].strip()
    final_alias = raw_alias if raw_alias else None

    if prop_str:
        props = _parse_prop_str(query, prop_str, prop_start)
    else:
        props = {}

    label_list = [lbl.strip() for lbl in alias_labels[1:]]
    if "labels" in props:
        props["__labels"] = props["labels"]
    props["labels"] = sorted(label_list)

    return final_alias, props


def _get_snippet(q: str, idx: int, context: int = 15) -> str:
    start = max(0, idx - context)
    end = min(len(q), idx + context)

    return q[start:end].replace("\n", " ")


def from_gql_create(query: str) -> VisualizationGraph:
    """
    Parse a GQL CREATE query and return a VisualizationGraph object representing the graph it creates.

    All node and relationship properties will be included in the visualization graph.
    All properties of nodes and relationships will be included in the `properties` dictionary of the respective objects.
    Additionally, a "labels" property will be added for nodes and a "type" property for relationships.

    By default:

    * the caption of a node will be based on its `labels`.
    * the caption of a relationship will be based on its `type`.
    * the color of nodes will be set based on their label, unless there are more than 12 unique labels.

    Please note that this function is not a full GQL parser, it only handles CREATE queries that do not contain
    other clauses like MATCH, WHERE, RETURN, etc, or any Cypher function calls.
    It also does not handle all possible GQL syntax, but it should work for most common cases.
    For more complex cases, we recommend using a Neo4j database and the `from_neo4j` method.

    Parameters
    ----------
    query : str
        The GQL CREATE query to parse
    """

    query = query.strip()
    if not re.match(r"(?i)^create\b", query):
        raise ValueError("Query must begin with 'CREATE' (case insensitive).")

    query = re.sub(r"(?i)^create\s*", "", query, count=1).rstrip(";").strip()
    parts = []
    paren_level = 0
    bracket_level = 0
    current: list[str] = []
    for i, char in enumerate(query):
        if char == "(":
            paren_level += 1
        elif char == ")":
            paren_level -= 1
            if paren_level < 0:
                snippet = _get_snippet(query, i)
                raise ValueError(f"Unbalanced parentheses near: `{snippet}`.")
        if char == "[":
            bracket_level += 1
        elif char == "]":
            bracket_level -= 1
            if bracket_level < 0:
                snippet = _get_snippet(query, i)
                raise ValueError(f"Unbalanced square brackets near: `{snippet}`.")
        if char == "," and paren_level == 0 and bracket_level == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)

    parts.append("".join(current).strip())
    if paren_level != 0:
        snippet = _get_snippet(query, len(query) - 1)
        raise ValueError(f"Unbalanced parentheses near: `{snippet}`.")
    if bracket_level != 0:
        snippet = _get_snippet(query, len(query) - 1)
        raise ValueError(f"Unbalanced square brackets near: `{snippet}`.")

    node_pattern = re.compile(r"^\(([^)]*)\)$")
    rel_pattern = re.compile(r"^\(([^)]*)\)-\s*\[\s*:(\w+)\s*(\{[^}]*\})?\s*\]->\(([^)]*)\)$")

    def _parse_validation_error(e: ValidationError, entity_type: type[BaseModel]) -> None:
        for err in e.errors():
            loc = err["loc"][0]
            raise ValueError(
                f"Error for {entity_type.__name__.lower()} property '{loc}' with provided input '{err['input']}'. Reason: {err['msg']}"
            )

    nodes = []
    relationships = []
    alias_to_id = {}
    anonymous_count = 0

    for part in parts:
        node_m = node_pattern.match(part)
        if node_m:
            alias_labels_props = node_m.group(1).strip()
            alias, props = _parse_labels_and_props(query, alias_labels_props)
            if not alias:
                alias = f"_anon_{anonymous_count}"
                anonymous_count += 1
            if alias not in alias_to_id:
                alias_to_id[alias] = str(uuid.uuid4())
            try:
                nodes.append(Node(id=alias_to_id[alias], properties=props))
            except ValidationError as e:
                _parse_validation_error(e, Node)

            continue

        rel_m = rel_pattern.match(part)
        if rel_m:
            left_node = rel_m.group(1).strip()
            right_node = rel_m.group(4).strip()

            # Parse left node pattern
            left_alias, left_props = _parse_labels_and_props(query, left_node)
            if not left_alias:
                left_alias = f"_anon_{anonymous_count}"
                anonymous_count += 1
                if left_alias not in alias_to_id:
                    alias_to_id[left_alias] = str(uuid.uuid4())
                try:
                    nodes.append(Node(id=alias_to_id[left_alias], properties=left_props))
                except ValidationError as e:
                    _parse_validation_error(e, Node)
            elif left_alias not in alias_to_id:
                snippet = _get_snippet(query, query.index(left_node))
                raise ValueError(f"Relationship references unknown node alias: '{left_alias}' near: `{snippet}`.")

            # Parse right node pattern
            right_alias, right_props = _parse_labels_and_props(query, right_node)
            if not right_alias:
                right_alias = f"_anon_{anonymous_count}"
                anonymous_count += 1
                if right_alias not in alias_to_id:
                    alias_to_id[right_alias] = str(uuid.uuid4())
                try:
                    nodes.append(Node(id=alias_to_id[right_alias], properties=right_props))
                except ValidationError as e:
                    _parse_validation_error(e, Node)
            elif right_alias not in alias_to_id:
                snippet = _get_snippet(query, query.index(right_node))
                raise ValueError(f"Relationship references unknown node alias: '{right_alias}' near: `{snippet}`.")

            rel_id = str(uuid.uuid4())
            rel_type = rel_m.group(2).replace(":", "").strip()
            rel_props_str = rel_m.group(3) or ""
            if rel_props_str:
                inner_str = rel_props_str.strip("{}").strip()
                prop_start = query.index(inner_str, query.index(inner_str))
                props = _parse_prop_str(query, inner_str, prop_start)
            else:
                props = {}
            if "type" in props:
                props["__type"] = props["type"]
            props["type"] = rel_type

            try:
                relationships.append(
                    Relationship(
                        id=rel_id,
                        source=alias_to_id[left_alias],
                        target=alias_to_id[right_alias],
                        properties=props,
                    )
                )
            except ValidationError as e:
                _parse_validation_error(e, Relationship)

            continue

        snippet = part[:30]
        raise ValueError(f"Invalid element in CREATE near: `{snippet}`.")

    VG = VisualizationGraph(nodes=nodes, relationships=relationships)

    for node in VG.nodes:
        node.caption = ":".join([label for label in node.properties["labels"]])
    for rel in VG.relationships:
        rel.caption = rel.properties.get("type")

    number_of_colors = len({str(n.properties.get("labels")) for n in VG.nodes})
    if number_of_colors <= len(NEO4J_COLORS_DISCRETE):
        VG.color_nodes(property="labels", color_space=ColorSpace.DISCRETE)

    return VG
