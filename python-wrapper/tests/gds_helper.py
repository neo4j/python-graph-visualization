import logging
import os
import re

from graphdatascience import GdsSessions, GraphDataScience
from graphdatascience.arrow_client.arrow_authentication import UsernamePasswordAuthentication
from graphdatascience.semantic_version.semantic_version import SemanticVersion
from graphdatascience.session import AuraAPICredentials, AuraGraphDataScience, DbmsConnectionInfo, SessionMemory
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


def connect_to_plugin_gds(uri: str, auth: tuple[str, str]) -> GraphDataScience:
    return GraphDataScience(endpoint=uri, auth=auth, database="neo4j")


def connect_to_local_gds_session(session_uri: str, db_uri: str, db_auth: tuple[str, str]) -> AuraGraphDataScience:
    session_bolt_connection_info = DbmsConnectionInfo(uri=session_uri, username="neo4j", password="password")
    db_connection_info = DbmsConnectionInfo(uri=db_uri, username=db_auth[0], password=db_auth[1])

    return AuraGraphDataScience.create(
        session_bolt_connection_info=session_bolt_connection_info,
        arrow_authentication=UsernamePasswordAuthentication("neo4j", "password"),
        session_lifecycle_manager=None,  # type: ignore
        db_endpoint=db_connection_info,
    )


def aura_api() -> AuraApi:
    if GDS_VERSION >= SemanticVersion(1, 15, 0):
        return AuraApi(
            client_id=os.environ["AURA_API_CLIENT_ID"],
            client_secret=os.environ["AURA_API_CLIENT_SECRET"],
            project_id=os.environ.get("AURA_API_PROJECT_ID"),
        )
    else:
        return AuraApi(
            client_id=os.environ["AURA_API_CLIENT_ID"],
            client_secret=os.environ["AURA_API_CLIENT_SECRET"],
            tenant_id=os.environ.get("AURA_API_PROJECT_ID"),  # type: ignore
        )


def gds_sessions() -> GdsSessions:
    return GdsSessions(
        api_credentials=AuraAPICredentials(
            client_id=os.environ["AURA_API_CLIENT_ID"],
            client_secret=os.environ["AURA_API_CLIENT_SECRET"],
            project_id=os.environ.get("AURA_API_PROJECT_ID"),
        )
    )


def create_auradb_instance(api: AuraApi) -> InstanceCreateDetails:
    type = (
        "enterprise-db" if os.environ.get("AURA_ENTERPRISE_PROJECT", "false").lower() == "true" else "professional-db"
    )
    instance_details: InstanceCreateDetails = api.create_instance(
        name="ci-neo4j-viz-db",
        memory=SessionMemory.m_2GB.value,
        cloud_provider="gcp",
        region="europe-west1",
        type=type,
    )
    logger = logging.getLogger(__name__)
    logger.debug(f"Created instance with ID: {instance_details.id}")

    return instance_details


def wait_for_instance(api: AuraApi, instance_details: InstanceCreateDetails) -> DbmsConnectionInfo:
    wait_result = api.wait_for_instance_running(instance_id=instance_details.id, max_wait_time=600)
    if wait_result.error:
        raise Exception(f"Error while waiting for instance to be running: {wait_result.error}")

    return DbmsConnectionInfo(
        username="neo4j",
        password=instance_details.password,
        aura_instance_id=instance_details.id,
        uri=wait_result.connection_url,
    )
