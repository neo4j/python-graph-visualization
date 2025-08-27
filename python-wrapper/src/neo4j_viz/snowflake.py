from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Optional

from pandas import DataFrame
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
)
from pydantic_core.core_schema import ValidationInfo
from snowflake.snowpark import Session
from snowflake.snowpark.exceptions import SnowparkSQLException
from snowflake.snowpark.types import (
    ArrayType,
    BooleanType,
    ByteType,
    DataType,
    DateType,
    DecimalType,
    DoubleType,
    FloatType,
    GeographyType,
    GeometryType,
    IntegerType,
    LongType,
    MapType,
    ShortType,
    StringType,
    StructField,
    StructType,
    TimestampType,
    TimeType,
    VariantType,
    VectorType,
)

from neo4j_viz import VisualizationGraph
from neo4j_viz.colors import ColorSpace
from neo4j_viz.pandas import from_dfs


def _data_type_name(type: DataType) -> str:
    if isinstance(type, StringType):
        return "VARCHAR"
    elif isinstance(type, LongType):
        return "BIGINT"
    elif isinstance(type, IntegerType):
        return "INT"
    elif isinstance(type, DoubleType):
        return "DOUBLE"
    elif isinstance(type, DecimalType):
        return "NUMBER"
    elif isinstance(type, BooleanType):
        return "BOOLEAN"
    elif isinstance(type, ByteType):
        return "TINYINT"
    elif isinstance(type, DateType):
        return "DATE"
    elif isinstance(type, ShortType):
        return "SMALLINT"
    elif isinstance(type, FloatType):
        return "FLOAT"
    elif isinstance(type, ArrayType):
        return "ARRAY"
    elif isinstance(type, VectorType):
        return "VECTOR"
    elif isinstance(type, MapType):
        return "OBJECT"
    elif isinstance(type, TimeType):
        return "TIME"
    elif isinstance(type, TimestampType):
        return "TIMESTAMP"
    elif isinstance(type, VariantType):
        return "VARIANT"
    elif isinstance(type, GeographyType):
        return "GEOGRAPHY"
    elif isinstance(type, GeometryType):
        return "GEOMETRY"
    else:
        # This actually does the job much of the time anyway
        return type.simple_string().upper()


SUPPORTED_ID_TYPES = [_data_type_name(data_type) for data_type in [StringType(), LongType(), IntegerType()]]


def _validate_id_column(schema: StructType, column_name: str, index: int, supported_types: list[str]) -> None:
    if column_name.lower() not in [name.lower() for name in schema.names]:
        raise ValueError(f"Schema must contain a `{column_name}` column")

    field: StructField = schema.fields[index]

    if field.name.lower() != column_name.lower():
        raise ValueError(f"Column `{column_name}` must have column index {index}")

    if _data_type_name(field.datatype) not in supported_types:
        raise ValueError(
            f"Column `{column_name}` has invalid type `{_data_type_name(field.datatype)}`. Expected one of [{', '.join(supported_types)}]"
        )


def _validate_viz_node_table(table: str, info: ValidationInfo) -> str:
    context = info.context
    if context and context["session"] is not None:
        session = context["session"]
        try:
            schema = session.table(table).schema
            _validate_id_column(schema, "nodeId", 0, SUPPORTED_ID_TYPES)
        except SnowparkSQLException as e:
            raise ValueError(f"Table '{table}' does not exist or is not accessible.") from e
    return table


def _validate_viz_relationship_table(
    table: str,
    info: ValidationInfo,
) -> str:
    context = info.context
    if context and context["session"] is not None:
        session = context["session"]
        try:
            schema = session.table(table).schema
            _validate_id_column(schema, "sourceNodeId", 0, SUPPORTED_ID_TYPES)
            _validate_id_column(schema, "targetNodeId", 1, SUPPORTED_ID_TYPES)
        except SnowparkSQLException as e:
            raise ValueError(f"Table '{table}' does not exist or is not accessible.") from e
    return table


def _parse_identifier_groups(identifier: str) -> list[str]:
    """
    Parses a table identifier into a list of individual identifier groups.

    This function handles identifiers that may include double-quoted segments
    and ensures proper validation of the identifier's structure. It raises
    errors for invalid formats, such as unbalanced quotes, invalid characters,
    or improper use of dots.

    Args:
        identifier (str): The input string identifier to parse.

    Returns:
        list[str]: A list of parsed identifier groups.

    Raises:
        ValueError: If the identifier contains:
            - Empty double quotes.
            - Consecutive dots outside of double quotes.
            - Unbalanced double quotes.
            - Invalid characters in unquoted segments.
            - Improper placement of dots around double-quoted segments.
    """
    inside = False  # Tracks whether the current character is inside double quotes
    quoted_starts = []  # Stores the start indices of double-quoted segments
    quoted_ends = []  # Stores the end indices of double-quoted segments
    remaining = ""  # Stores the unquoted part of the identifier
    previous_is_dot = False  # Tracks if the previous character was a dot

    for i, c in enumerate(identifier):
        if c == '"':
            if not inside:
                quoted_starts.append(i + 1)  # Mark the start of a quoted segment
                previous_is_dot = False
            else:
                quoted_ends.append(i)  # Mark the end of a quoted segment
                if quoted_ends[-1] - quoted_starts[-1] == 0:
                    raise ValueError("Empty double quotes")
            inside = not inside  # Toggle the inside state
        else:
            if not inside:
                remaining += c  # Append unquoted characters to `remaining`
                if c == ".":
                    if previous_is_dot:
                        raise ValueError("Not ok to have consecutive dots outside of double quote")
                    previous_is_dot = True
                else:
                    previous_is_dot = False

    if len(quoted_starts) != len(quoted_ends):
        raise ValueError("Unbalanced double quotes")

    for quoted_start in quoted_starts:
        if quoted_start > 1:
            if identifier[quoted_start - 2] != ".":
                raise ValueError("Only dot character may precede before double quoted identifier")

    for quoted_end in quoted_ends:
        if quoted_end < len(identifier) - 1:
            if identifier[quoted_end + 1] != ".":
                raise ValueError("Only dot character may follow double quoted identifier")

    words = remaining.split(".")  # Split the unquoted part by dots
    for word in words:
        if len(word) == 0:
            continue
        if word.lower()[0] not in "abcdefghijklmnopqrstuvwxyz_":
            raise ValueError(f"Invalid first character in identifier {word}. Only a-z, A-Z, and _ are allowed.")
        if not set(word.lower()).issubset(set("abcdefghijklmnopqrstuvwxyz$_0123456789")):
            raise ValueError(f"Invalid characters in identifier {word}. Only a-z, A-Z, 0-9, _, and $ are allowed.")

    empty_words_idx = [i for i, w in enumerate(words) if w == ""]
    for i in range(len(quoted_starts)):
        # Replace empty words with their corresponding quoted segments
        words[empty_words_idx[i]] = f'"{identifier[quoted_starts[i] : quoted_ends[i]]}"'

    return words


def _validate_table_name(table: str) -> str:
    if not isinstance(table, str):
        raise TypeError(f"Table name must be a string, got {type(table).__name__}")

    try:
        words = _parse_identifier_groups(table)
    except ValueError as e:
        raise ValueError(f"Invalid table name '{table}'. {str(e)}") from e

    if len(words) not in {1, 3}:
        raise ValueError(
            f"Invalid table name '{table}'. Table names must be in the format '<database>.<schema>.<table>' or '<table>'"
        )

    return table


Table = Annotated[str, BeforeValidator(_validate_table_name)]

VizNodeTable = Annotated[Table, AfterValidator(_validate_viz_node_table)]
VizRelationshipTable = Annotated[Table, AfterValidator(_validate_viz_relationship_table)]


class Orientation(Enum):
    NATURAL = "natural"
    UNDIRECTED = "undirected"
    REVERSE = "reverse"


def _to_lower(value: str) -> str:
    return value.lower() if value and isinstance(value, str) else value


LowercaseOrientation = Annotated[Orientation, BeforeValidator(_to_lower)]


class VizRelationshipTableConfig(BaseModel, extra="forbid"):
    sourceTable: VizNodeTable
    targetTable: VizNodeTable
    orientation: Optional[LowercaseOrientation] = Orientation.NATURAL


class VizProjectConfig(BaseModel, extra="forbid"):
    defaultTablePrefix: Optional[str] = None
    nodeTables: list[VizNodeTable]
    relationshipTables: dict[VizRelationshipTable, VizRelationshipTableConfig]


def _map_tables(
    session: Session, project_model: VizProjectConfig
) -> tuple[list[DataFrame], list[DataFrame], list[str]]:
    offset = 0
    to_internal = {}
    node_dfs = []
    for table in project_model.nodeTables:
        df = session.table(table).to_pandas()
        internal_ids = range(offset, offset + df.shape[0])
        to_internal[table] = df[["NODEID"]].copy()
        to_internal[table]["INTERNALID"] = internal_ids
        offset += df.shape[0]

        df["SNOWFLAKEID"] = df["NODEID"]
        df["NODEID"] = internal_ids

        node_dfs.append(df)

    rel_dfs = []
    rel_table_names = []
    for table, rel_table_config in project_model.relationshipTables.items():
        df = session.table(table).to_pandas()

        source_table = rel_table_config.sourceTable
        target_table = rel_table_config.targetTable

        df = df.merge(to_internal[source_table], left_on="SOURCENODEID", right_on="NODEID")
        df.drop(["SOURCENODEID", "NODEID"], axis=1, inplace=True)
        df.rename({"INTERNALID": "SOURCENODEID"}, axis=1, inplace=True)
        df = df.merge(to_internal[target_table], left_on="TARGETNODEID", right_on="NODEID")
        df.drop(["TARGETNODEID", "NODEID"], axis=1, inplace=True)
        df.rename({"INTERNALID": "TARGETNODEID"}, axis=1, inplace=True)

        if (
            rel_table_config.orientation == Orientation.NATURAL
            or rel_table_config.orientation == Orientation.UNDIRECTED
        ):
            rel_dfs.append(df)
            rel_table_names.append(table)

        if rel_table_config.orientation == Orientation.REVERSE:
            df_rev = df.rename(columns={"SOURCENODEID": "TARGETNODEID", "TARGETNODEID": "SOURCENODEID"}, copy=False)
            rel_dfs.append(df_rev)
            rel_table_names.append(table)

        if rel_table_config.orientation == Orientation.UNDIRECTED:
            df_rev = df.rename(columns={"SOURCENODEID": "TARGETNODEID", "TARGETNODEID": "SOURCENODEID"}, copy=True)
            rel_dfs.append(df_rev)
            rel_table_names.append(table)

    return node_dfs, rel_dfs, rel_table_names


def from_snowflake(
    session: Session,
    project_config: dict[str, Any],
    node_radius_min_max: Optional[tuple[float, float]] = (3, 60),
) -> VisualizationGraph:
    project_model = VizProjectConfig.model_validate(project_config, strict=False, context={"session": session})
    node_dfs, rel_dfs, rel_table_names = _map_tables(session, project_model)

    node_caption_present = False
    for node_df in node_dfs:
        if "CAPTION" in node_df.columns:
            node_caption_present = True
            break

    if not node_caption_present:
        for i, node_df in enumerate(node_dfs):
            node_df["caption"] = project_model.nodeTables[i].split(".")[-1]

    rel_caption_present = False
    for rel_df in rel_dfs:
        if "CAPTION" in rel_df.columns:
            rel_caption_present = True
            break

    if not rel_caption_present:
        for i, rel_df in enumerate(rel_dfs):
            rel_df["caption"] = rel_table_names[i].split(".")[-1]

    VG = from_dfs(node_dfs, rel_dfs, node_radius_min_max)

    VG.color_nodes(field="caption", color_space=ColorSpace.DISCRETE)

    return VG
