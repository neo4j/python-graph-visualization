import os
import re

from graphdatascience import GraphDataScience
from graphdatascience.semantic_version.semantic_version import SemanticVersion
from graphdatascience.session import DbmsConnectionInfo, SessionMemory
from graphdatascience.session.aura_api import AuraApi
from graphdatascience.session.aura_api_responses import InstanceCreateDetails
from graphdatascience.version import __version__


def parse_version(version: str) -> SemanticVersion:
    server_version_match = re.search(r"(\d+\.)?(\d+\.)?(\*|\d+)", version)
    if not server_version_match:
        raise ValueError(f"{version} is not a valid semantic version")

    groups = [int(g.replace(".", "")) for g in server_version_match.groups() if g]

    major = groups[0] if len(groups) > 0 else 0
    minor = groups[1] if len(groups) > 1 else 0
    patch = groups[2] if len(groups) > 2 else 0

    return SemanticVersion(major=major, minor=minor, patch=patch)


GDS_VERSION = parse_version(__version__)


def connect_to_plugin_gds(uri: str) -> GraphDataScience:
    NEO4J_AUTH = ("neo4j", "password")
    if os.environ.get("NEO4J_USER"):
        NEO4J_AUTH = (os.environ.get("NEO4J_USER", "DUMMY"), os.environ.get("NEO4J_PASSWORD", "neo4j"))

    return GraphDataScience(endpoint=uri, auth=NEO4J_AUTH, database="neo4j")


def aura_api() -> AuraApi:
    if GDS_VERSION >= SemanticVersion(1, 15, 0):
        return AuraApi(
            client_id=os.environ["AURA_API_CLIENT_ID"],
            client_secret=os.environ["AURA_API_CLIENT_SECRET"],
            project_id=os.environ.get("AURA_API_TENANT_ID"),
        )
    else:
        return AuraApi(
            client_id=os.environ["AURA_API_CLIENT_ID"],
            client_secret=os.environ["AURA_API_CLIENT_SECRET"],
            tenant_id=os.environ.get("AURA_API_TENANT_ID"),  # type: ignore
        )


def create_aurads_instance(api: AuraApi) -> tuple[str, DbmsConnectionInfo]:
    # Switch to Sessions once they can be created without a DB
    instance_details: InstanceCreateDetails = api.create_instance(
        name="ci-neo4j-viz-session",
        memory=SessionMemory.m_8GB.value,
        cloud_provider="gcp",
        region="europe-west1",
    )

    wait_result = api.wait_for_instance_running(instance_id=instance_details.id)
    if wait_result.error:
        raise Exception(f"Error while waiting for instance to be running: {wait_result.error}")

    return instance_details.id, DbmsConnectionInfo(
        uri=wait_result.connection_url,
        username="neo4j",
        password=instance_details.password,
    )
