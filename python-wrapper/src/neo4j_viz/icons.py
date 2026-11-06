from __future__ import annotations

import base64
import warnings
from enum import StrEnum
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

#: File extensions we can inline as a data URI, mapped to their MIME type.
_MIME_TYPES = {
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

#: Content types accepted when fetching a remote icon.
_SUPPORTED_CONTENT_TYPES = set(_MIME_TYPES.values())

#: Timeout in seconds for fetching a remote icon.
_FETCH_TIMEOUT_SECONDS = 10.0

#: Maximum size of a remote icon in bytes, to catch non-icon files.
_MAX_ICON_BYTES = 1024 * 1024


class Icons(StrEnum):
    """
    Built-in icons that can be assigned to `Node.icon` and `OverlayIcon.url`.

    The names mirror the Neo4j design system icon set
    (https://storybook-components-build.appspot.com/?path=/docs/icons-icon-finder--docs).
    Any icon not listed here can still be used by passing a URL instead of a name.
    """

    BOOLEAN = "boolean"
    CHIP = "chip"
    CIRCLE = "circle"
    CLOUD_CHECK = "cloud_check"
    CLOUD_CROSS = "cloud_cross"
    CONFIGURE = "configure"
    DATABASE_CHECK = "database_check"
    DATABASE_CROSS = "database_cross"
    DATABASE_PLUG = "database_plug"
    DATABASE_PLUS = "database_plus"
    DATABASE_ROLE = "database_role"
    DATABASE_SIGNAL = "database_signal"
    DATA_SCIENCE = "data_science"
    DEPLOYMENTS = "deployments"
    DESKTOP_SAVE = "desktop_save"
    DOCUMENT_INTELLIGENCE = "document_intelligence"
    DOCUMENT_REFRESH = "document_refresh"
    EXPLORE = "explore"
    EXTERNAL_LINK = "external_link"
    FLOPPY_DISK = "floppy_disk"
    FOLDER_BOOKMARK = "folder_bookmark"
    GITHUB = "github"
    GLOBE_PIN = "globe_pin"
    GRAPH_BUILDER = "graph_builder"
    GRAPH_CROSS = "graph_cross"
    HEADSET = "headset"
    HEARTBEAT = "heartbeat"
    HIERARCHY_ONE = "hierarchy_one"
    HIERARCHY_TWO = "hierarchy_two"
    LIST_CHECK = "list_check"
    LIST_NUMBER = "list_number"
    LOCATION_TARGET = "location_target"
    MEMORY_CARD = "memory_card"
    NODE_ADD = "node_add"
    NODE_CLICK = "node_click"
    PIN = "pin"
    PRESENTATION = "presentation"
    QUERY = "query"
    QUERY_STREAM = "query_stream"
    RELATIONSHIP_ADD = "relationship_add"
    RELATIONSHIP_CLICK = "relationship_click"
    RHOMBUS = "rhombus"
    SCATTER_PLOT = "scatter_plot"
    SELECT = "select"
    SINGLE_VALUE = "single_value"
    SQUARE = "square"
    TEXT = "text"
    TRIANGLE = "triangle"
    USER_SHIELD = "user_shield"
    VISUALIZE_BLOOM = "visualize_bloom"


def icon_from_svg(svg: str) -> str:
    """
    Turn an SVG string into a data URI usable as an icon.

    Icons should be square and black: the visualization inverts black icons to white when they
    are drawn on a dark node color.

    Parameters
    ----------
    svg:
        The SVG markup, for example the contents of an ``.svg`` file.

    Returns
    -------
    str
        A ``data:image/svg+xml`` URI.
    """
    return "data:image/svg+xml," + quote(svg, safe="")


def icon_from_file(path: str | Path) -> str:
    """
    Turn a local image file into a data URI usable as an icon.

    This lets a notebook stay self-contained: the visualization runs in a browser and cannot
    read local file paths, so the file is inlined instead of referenced.

    Icons should be square and black: the visualization inverts black icons to white when they
    are drawn on a dark node color.

    Parameters
    ----------
    path:
        Path to an image file. Supported formats are SVG, PNG, JPEG, GIF and WebP.

    Returns
    -------
    str
        A data URI that can be assigned to `Node.icon` or `OverlayIcon.url`.
    """
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    mime_type = _MIME_TYPES.get(suffix)

    if mime_type is None:
        supported = ", ".join(sorted(_MIME_TYPES))
        raise ValueError(f"Unsupported icon file type '{suffix}' for {file_path}. Supported types are: {supported}")

    data = file_path.read_bytes()

    if suffix == ".svg":
        return icon_from_svg(data.decode("utf-8"))

    return f"data:{mime_type};base64," + base64.b64encode(data).decode("ascii")


def icons_from_directory(path: str | Path) -> dict[str, str]:
    """
    Build a mapping from icon name to data URI for the image files in a directory.

    The name of an icon is its filename without the extension, so naming the files after your node
    categories lets you pass the result straight to `VisualizationGraph.set_node_icons`:

    >>> VG.set_node_icons(property="label", mapping=icons_from_directory("assets/icons"))

    Only the top level of the directory is scanned. Supported formats are SVG, PNG, JPEG, GIF and
    WebP; other files are skipped with a warning, and hidden files are skipped silently. If two
    files share the same name, a `ValueError` is raised.

    Parameters
    ----------
    path:
        Path to a directory containing image files.

    Returns
    -------
    dict[str, str]
        A mapping from icon name to data URI.
    """
    directory = Path(path)

    if not directory.is_dir():
        raise ValueError(f"Icon directory '{directory}' does not exist or is not a directory")

    icons: dict[str, str] = {}
    sources: dict[str, str] = {}

    for file in sorted(directory.iterdir()):
        if not file.is_file() or file.name.startswith("."):
            continue

        if file.suffix.lower() not in _MIME_TYPES:
            warnings.warn(f"Skipping '{file.name}': not a supported image type", stacklevel=2)
            continue

        if file.stem in icons:
            raise ValueError(
                f"Duplicate icon name '{file.stem}': both '{sources[file.stem]}' and '{file.name}' map to it"
            )

        icons[file.stem] = icon_from_file(file)
        sources[file.stem] = file.name

    return icons


def icon_from_url(url: str) -> str:
    """
    Download a remote image and inline it as a data URI.

    The download happens in Python, so the visualization does not need to reach the host, and hosts
    that do not send CORS headers (which the browser requires for icons) still work. This also keeps
    a notebook self-contained: the icon is embedded instead of referenced.

    Icons should be square and black: the visualization inverts black icons to white when they are
    drawn on a dark node color.

    Parameters
    ----------
    url:
        URL of the image, using the ``http`` or ``https`` scheme. A ``data:`` URI is returned
        unchanged.

    Returns
    -------
    str
        A data URI that can be assigned to `Node.icon` or `OverlayIcon.url`.
    """
    if url.startswith("data:"):
        return url

    scheme = urlsplit(url).scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError(
            f"Unsupported icon URL scheme '{scheme}' for {url}. Use an http(s) URL, "
            "`icon_from_file` for a local file, or a name from `Icons`."
        )

    request = Request(url, headers={"User-Agent": "neo4j-viz"})
    with urlopen(request, timeout=_FETCH_TIMEOUT_SECONDS) as response:
        content_type = response.headers.get_content_type()
        if content_type not in _SUPPORTED_CONTENT_TYPES:
            supported = ", ".join(sorted(_SUPPORTED_CONTENT_TYPES))
            raise ValueError(
                f"URL {url} returned content type '{content_type}', which is not a supported image type. "
                f"Supported types are: {supported}"
            )

        # Read one byte past the limit so an oversized file is detected without buffering all of it.
        data = response.read(_MAX_ICON_BYTES + 1)

    if len(data) > _MAX_ICON_BYTES:
        raise ValueError(f"Icon at {url} is larger than the maximum of {_MAX_ICON_BYTES} bytes")

    if content_type == "image/svg+xml":
        return icon_from_svg(data.decode("utf-8"))

    return f"data:{content_type};base64," + base64.b64encode(data).decode("ascii")
