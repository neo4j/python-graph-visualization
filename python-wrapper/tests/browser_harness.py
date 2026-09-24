"""Headless-browser machinery for executing notebooks that need a live frontend.

Boots a disposable JupyterLab server, drives a notebook cell by cell in
headless Chrome via Playwright, and waits for kernel-side marker files.
``GraphWidget.save()`` only works with a mounted frontend, so plain headless
kernel execution (nbclient) is not enough for anything that saves images.

Used by the ``GraphWidget.save()`` end-to-end test and by the docs image
regeneration utility (``scripts/regenerate_docs_images.py``).
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
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import nbformat
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

SERVER_START_TIMEOUT = 60
LAB_LOAD_TIMEOUT = 40
CELL_RUN_TIMEOUT = 15
CELL_COMPLETE_TIMEOUT = 90
WIDGET_MOUNT_TIMEOUT = 30
NOTEBOOK_RUN_TIMEOUT = 120

# Kernel-side marker files written by the last notebook cell: ``_done.txt`` on
# success, ``_error.txt`` with the traceback on failure.
DONE_MARKER = "_done.txt"
ERROR_MARKER = "_error.txt"

# A rendered NVL widget shows as a canvas in the cell's output area. Every
# notebook driven by this harness renders the widget in one cell and exercises
# it in the next, so waiting for the canvas before the last cell generically
# covers "the widget is mounted before we interact with it".
WIDGET_CANVAS_SELECTOR = ".jp-OutputArea canvas"


class BrowserUnavailableError(RuntimeError):
    """Raised when neither system Chrome nor bundled Chromium can be launched."""


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


@contextmanager
def jupyter_server(root: Path) -> Iterator[JupyterServer]:
    """Boot a disposable, tokenless JupyterLab server rooted at ``root``.

    The server process is terminated when the context exits. The kernel runs
    with ``root`` as its working directory, so files written by notebook cells
    (markers, saved images) land there.
    """
    jupyter_dir = root / ".jupyter"
    jupyter_dir.mkdir(exist_ok=True)
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
                # Notebooks are created below via the contents REST API; the
                # server would reject that PUT with 403 (CSRF check on non-GET
                # requests). Fine on an ephemeral localhost-only server.
                "--ServerApp.disable_check_xsrf=True",
                # Saved Lab workspaces are NOT covered by JUPYTER_CONFIG_DIR
                # either. Their ids only hash the URL, so every server would
                # map to the same workspace in ~/.jupyter and try to reopen the
                # previous run's (now missing) notebook.
                f"--LabApp.workspaces_dir={jupyter_dir / 'lab-workspaces'}",
                f"--ServerApp.root_dir={root}",
            ],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            # Isolate the server from the host user's Jupyter config (~/.jupyter);
            # without this, locally installed extensions or settings would leak
            # into the server.
            env={**os.environ, "JUPYTER_CONFIG_DIR": str(jupyter_dir)},
        )
    server = JupyterServer(url=f"http://127.0.0.1:{port}", root=root, process=process, log_path=log_path)
    try:
        _wait_until_ready(server)
        yield server
    finally:
        process.terminate()
        process.wait(timeout=10)


def create_notebook(server: JupyterServer, cells: Sequence[str]) -> str:
    """Create a notebook with the given code cells via the contents REST API."""
    notebook = nbformat.v4.new_notebook(  # type: ignore[no-untyped-call]
        cells=[nbformat.v4.new_code_cell(cell) for cell in cells],  # type: ignore[no-untyped-call]
        metadata={"kernelspec": {"display_name": "Python 3 (ipykernel)", "language": "python", "name": "python3"}},
    )
    name = f"nb-{uuid.uuid4().hex[:8]}.ipynb"
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
    deadline = time.monotonic() + SERVER_START_TIMEOUT
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{server.url}/api", timeout=2):
                return
        except (urllib.error.URLError, OSError):
            time.sleep(0.25)
    raise RuntimeError(f"JupyterLab did not start within {SERVER_START_TIMEOUT}s; log:\n{server.log_path.read_text()}")


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
    raise BrowserUnavailableError(
        "no Chrome/Chromium available: install Google Chrome or run `uv run playwright install chromium`"
    )


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
        expect(prompt).not_to_have_text("[ ]:", timeout=CELL_RUN_TIMEOUT * 1000)
    except AssertionError as exc:
        raise AssertionError(
            f"cell {index} did not start executing after Shift+Enter (prompt is still "
            f"{prompt.text_content()!r}; a dialog may be blocking keyboard input)"
        ) from exc
    # Also wait for the cell to finish (its prompt gets an execution count): a slow
    # kernel — e.g. cold imports on a loaded CI runner — would otherwise eat into
    # the widget-mount timeout below, which is only meant to cover the frontend
    # rendering the already-displayed widget.
    expect(prompt).to_have_text(re.compile(r"^\[\d+\]:$"), timeout=CELL_COMPLETE_TIMEOUT * 1000)


def _execute_notebook_in_browser(page: Page, cells: Sequence[str]) -> None:
    expect(page.locator(".jp-Cell")).to_have_count(len(cells), timeout=LAB_LOAD_TIMEOUT * 1000)
    for index in range(len(cells)):
        if index == len(cells) - 1:
            # The last cell exercises the widget; wait for the frontend to have
            # actually mounted it (a canvas) so we don't race its async
            # initialization — e.g. `save()` before the widget renders would
            # hit the "not rendered yet" reply.
            page.wait_for_selector(WIDGET_CANVAS_SELECTOR, timeout=WIDGET_MOUNT_TIMEOUT * 1000)
        _accept_visible_dialogs(page)
        _run_cell(page, index)


def _await_notebook_markers(server: JupyterServer) -> None:
    deadline = time.monotonic() + NOTEBOOK_RUN_TIMEOUT
    while time.monotonic() < deadline:
        error_marker = server.root / ERROR_MARKER
        if error_marker.exists():
            raise RuntimeError(f"notebook raised:\n{error_marker.read_text()}")
        if (server.root / DONE_MARKER).exists():
            return
        time.sleep(0.5)
    raise RuntimeError(f"notebook did not finish within {NOTEBOOK_RUN_TIMEOUT}s; log:\n{server.log_path.read_text()}")


def _dump_debug_artifacts(server: JupyterServer, page: Page, console_messages: Sequence[str]) -> None:
    page.screenshot(path=str(server.root / "debug-screenshot.png"))
    (server.root / "debug-page.html").write_text(page.content())
    (server.root / "debug-console.log").write_text("\n".join(console_messages))


def run_notebook_in_browser(server: JupyterServer, cells: Sequence[str]) -> None:
    """Create a notebook from ``cells`` on ``server`` and run it in headless Chrome.

    The last cell must write the ``_done.txt``/``_error.txt`` markers (see
    ``DONE_MARKER``/``ERROR_MARKER``); the second-to-last is expected to display
    a widget, which is awaited via its canvas before the last cell runs. Any
    browser console error fails the run, and failures dump debug artifacts
    (screenshot, page HTML, console log) into the server root.
    """
    for marker in (DONE_MARKER, ERROR_MARKER):
        (server.root / marker).unlink(missing_ok=True)
    notebook_name = create_notebook(server, cells)
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
                # A fresh workspace id per run: all /lab/tree URLs share the
                # `default` workspace, which restores every previously opened
                # notebook as an extra tab (and extra .jp-Cell elements).
                workspace = uuid.uuid4().hex[:8]
                page.goto(f"{server.url}/lab/workspaces/{workspace}/tree/{notebook_name}")
                _execute_notebook_in_browser(page, cells)
                _await_notebook_markers(server)
            except Exception:
                _dump_debug_artifacts(server, page, console_messages)
                raise
        finally:
            browser.close()
    if console_errors:
        raise RuntimeError(f"browser console errors: {console_errors}")
