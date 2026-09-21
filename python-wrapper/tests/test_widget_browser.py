"""End-to-end test for ``GraphWidget.save()`` in a real JupyterLab browser session.

Boots a disposable JupyterLab server, creates a notebook whose cells render a
widget and call ``save()``, drives it in headless Chrome via Playwright, and
verifies that the PNG/SVG files actually appear on the kernel side.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import nbformat
import pytest
from playwright.sync_api import (
    Browser,
    ConsoleMessage,
    Page,
    Playwright,
    expect,
    sync_playwright,
)
from playwright.sync_api import (
    Error as PlaywrightError,
)

_SERVER_START_TIMEOUT = 60
_LAB_LOAD_TIMEOUT = 40
_CELL_RUN_TIMEOUT = 15
_CELL_COMPLETE_TIMEOUT = 90
_WIDGET_MOUNT_TIMEOUT = 30
_NOTEBOOK_RUN_TIMEOUT = 120

# A rendered NVL widget shows as a canvas in the cell's output area. Every
# notebook driven by this harness renders the widget in one cell and exercises
# it in the next, so waiting for the canvas before the last cell generically
# covers "the widget is mounted before we interact with it".
_WIDGET_CANVAS_SELECTOR = ".jp-OutputArea canvas"


@dataclass
class JupyterServer:
    url: str
    root: Path
    process: subprocess.Popen[bytes]
    log_path: Path


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def jupyter_server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[JupyterServer]:
    root = tmp_path_factory.mktemp("lab-root")
    jupyter_dir = root / ".jupyter"
    jupyter_dir.mkdir()
    log_path = root / "jupyter-server.log"
    port = _free_port()
    with log_path.open("wb") as log_file:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "jupyter",
                "lab",
                "--no-browser",
                "--ip=127.0.0.1",
                f"--port={port}",
                "--ServerApp.port_retries=0",
                "--IdentityProvider.token=",
                # The notebook is created below via the contents REST API; the
                # server would reject that PUT with 403 (CSRF check on non-GET
                # requests). Fine on an ephemeral localhost-only test server.
                "--ServerApp.disable_check_xsrf=True",
                # Saved Lab workspaces are NOT covered by JUPYTER_CONFIG_DIR either.
                # Their ids only hash the URL, so every test server would map to the
                # same workspace in ~/.jupyter and try to reopen the previous run's
                # (now missing) notebook.
                f"--LabApp.workspaces_dir={jupyter_dir / 'lab-workspaces'}",
                f"--ServerApp.root_dir={root}",
            ],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            # Isolate the server from the host user's Jupyter config (~/.jupyter);
            # without this, locally installed extensions or settings would leak into
            # the test server.
            env={**os.environ, "JUPYTER_CONFIG_DIR": str(jupyter_dir)},
        )
    server = JupyterServer(url=f"http://127.0.0.1:{port}", root=root, process=process, log_path=log_path)
    try:
        _wait_until_ready(server)
        yield server
    finally:
        process.terminate()
        process.wait(timeout=10)


def _create_notebook(server: JupyterServer, cells: Sequence[str]) -> str:
    notebook = nbformat.v4.new_notebook(  # type: ignore[no-untyped-call]
        cells=[nbformat.v4.new_code_cell(cell) for cell in cells],  # type: ignore[no-untyped-call]
        metadata={"kernelspec": {"display_name": "Python 3 (ipykernel)", "language": "python", "name": "python3"}},
    )
    name = f"test-{uuid.uuid4().hex[:8]}.ipynb"
    body = {"type": "notebook", "format": "json", "content": json.loads(nbformat.writes(notebook))}  # type: ignore[no-untyped-call]
    request = urllib.request.Request(
        f"{server.url}/api/contents/{name}",
        data=json.dumps(body).encode("utf-8"),
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        json.loads(response.read().decode("utf-8"))
    return name


def _wait_until_ready(server: JupyterServer) -> None:
    deadline = time.monotonic() + _SERVER_START_TIMEOUT
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{server.url}/api", timeout=2):
                return
        except (urllib.error.URLError, OSError):
            time.sleep(0.25)
    pytest.fail(f"JupyterLab did not start within {_SERVER_START_TIMEOUT}s; log:\n{server.log_path.read_text()}")


def _launch_chromium(playwright: Playwright) -> Browser:
    # Prefer the system Chrome (also preinstalled on CI runners) so that no
    # `playwright install` download is needed; fall back to Playwright's
    # bundled Chromium if it happens to be installed.
    for channel in ("chrome", None):
        try:
            if channel is not None:
                return playwright.chromium.launch(channel=channel, headless=True)
            return playwright.chromium.launch(headless=True)
        except PlaywrightError:
            continue
    pytest.skip("no Chrome/Chromium available: install Google Chrome or run `uv run playwright install chromium`")


def _accept_visible_dialogs(page: Page) -> None:
    # On open, Lab can show a kernel-picker dialog that swallows keyboard input
    # until it is confirmed (the notebook's kernelspec usually prevents it, but
    # the dialog has been observed to appear anyway).
    for _ in range(3):
        accept = page.locator(".jp-Dialog:visible .jp-mod-accept")
        if accept.count() == 0:
            return
        accept.first.click()
        page.wait_for_timeout(300)


def _run_cell(page: Page, index: int) -> None:
    cell = page.locator(".jp-Cell").nth(index)
    prompt = cell.locator(".jp-InputArea-prompt")
    cell.click()
    page.keyboard.press("Shift+Enter")
    try:
        expect(prompt).not_to_have_text("[ ]:", timeout=_CELL_RUN_TIMEOUT * 1000)
    except AssertionError as exc:
        raise AssertionError(
            f"cell {index} did not start executing after Shift+Enter (prompt is still "
            f"{prompt.text_content()!r}; a dialog may be blocking keyboard input)"
        ) from exc
    # Also wait for the cell to finish (its prompt gets an execution count): a slow
    # kernel — e.g. cold imports on a loaded CI runner — would otherwise eat into
    # the widget-mount timeout below, which is only meant to cover the frontend
    # rendering the already-displayed widget.
    expect(prompt).to_have_text(re.compile(r"^\[\d+\]:$"), timeout=_CELL_COMPLETE_TIMEOUT * 1000)


def _execute_notebook_in_browser(page: Page, cells: Sequence[str]) -> None:
    expect(page.locator(".jp-Cell")).to_have_count(len(cells), timeout=_LAB_LOAD_TIMEOUT * 1000)
    for index in range(len(cells)):
        if index == len(cells) - 1:
            # The last cell exercises the widget; wait for the frontend to have
            # actually mounted it (a canvas) so we don't race its async
            # initialization — e.g. `save()` before the widget renders would
            # hit the "not rendered yet" reply.
            page.wait_for_selector(_WIDGET_CANVAS_SELECTOR, timeout=_WIDGET_MOUNT_TIMEOUT * 1000)
        _accept_visible_dialogs(page)
        _run_cell(page, index)


def _await_notebook_markers(server: JupyterServer) -> None:
    deadline = time.monotonic() + _NOTEBOOK_RUN_TIMEOUT
    while time.monotonic() < deadline:
        error_marker = server.root / "_error.txt"
        if error_marker.exists():
            pytest.fail(f"notebook raised:\n{error_marker.read_text()}")
        if (server.root / "_done.txt").exists():
            return
        time.sleep(0.5)
    pytest.fail(f"notebook did not finish within {_NOTEBOOK_RUN_TIMEOUT}s; log:\n{server.log_path.read_text()}")


def _dump_debug_artifacts(server: JupyterServer, page: Page, console_messages: Sequence[str]) -> None:
    page.screenshot(path=str(server.root / "debug-screenshot.png"))
    (server.root / "debug-page.html").write_text(page.content())
    (server.root / "debug-console.log").write_text("\n".join(console_messages))


def _run_notebook(server: JupyterServer, cells: Sequence[str]) -> None:
    for marker in ("_done.txt", "_error.txt"):
        (server.root / marker).unlink(missing_ok=True)
    notebook_name = _create_notebook(server, cells)
    console_messages: list[str] = []
    console_errors: list[str] = []

    def record_console(message: ConsoleMessage) -> None:
        entry = f"{message.type}: {message.text}"
        console_messages.append(entry)
        if message.type == "error":
            console_errors.append(entry)

    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.on("console", record_console)
            page.on("pageerror", lambda error: console_errors.append(f"uncaught page error: {error}"))
            try:
                page.goto(f"{server.url}/lab/tree/{notebook_name}")
                _execute_notebook_in_browser(page, cells)
                _await_notebook_markers(server)
            except Exception:
                _dump_debug_artifacts(server, page, console_messages)
                raise
        finally:
            browser.close()
    assert not console_errors, f"browser console errors: {console_errors}"


def test_save_png_and_svg_end_to_end(jupyter_server: JupyterServer) -> None:
    setup_cell = """\
from neo4j_viz import Node, Relationship, VisualizationGraph
nodes = [Node(id='0', caption='Alice'), Node(id='1', caption='Bob')]
rels = [Relationship(source='0', target='1', caption='KNOWS')]
widget = VisualizationGraph(nodes=nodes, relationships=rels).render_widget(height='400px')
widget
"""
    save_image_cell = """\
import traceback
from pathlib import Path
try:
    await widget.save('out.svg')
    await widget.save('out.png', background_color='#ffffff')
    assert Path('out.svg').read_text().lstrip().startswith('<svg')
    assert Path('out.png').read_bytes()[:8] == b'\\x89PNG\\r\\n\\x1a\\n'
    Path('_done.txt').write_text('ok')
except Exception:
    Path('_error.txt').write_text(traceback.format_exc())
"""
    _run_notebook(jupyter_server, [setup_cell, save_image_cell])

    svg = (jupyter_server.root / "out.svg").read_text()
    png = (jupyter_server.root / "out.png").read_bytes()
    assert svg.lstrip().startswith("<svg")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
