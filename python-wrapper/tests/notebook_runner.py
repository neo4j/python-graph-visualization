import pathlib
import re
import signal
import sys
from datetime import datetime
from typing import Any, NamedTuple

import nbformat
from nbclient.exceptions import CellExecutionError
from nbconvert.preprocessors.execute import ExecutePreprocessor

TEARDOWN_CELL_TAG = "teardown"

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
CELL_FRAME_RE = re.compile(r"Cell In\[\d+\], line \d+")


class IndexedCell(NamedTuple):
    cell: Any
    index: int  # type: ignore


class TeardownExecutePreprocessor(ExecutePreprocessor):
    def __init__(self, **kw: Any):
        super().__init__(**kw)  # type: ignore

    def init_notebook(self, tear_down_cells: list[IndexedCell]) -> None:
        self.tear_down_cells = tear_down_cells
        self._skip_rest = False
        self.failing_cell_index: int | None = None

    # run the cell of a notebook
    def preprocess_cell(self, cell: Any, resources: Any, index: int) -> None:
        if index == 0:

            def handle_signal(sig, frame):  # type: ignore
                print("Received SIGNAL, running tear down cells")
                self.teardown(resources)
                sys.exit(1)

            signal.signal(signal.SIGINT, handle_signal)
            signal.signal(signal.SIGTERM, handle_signal)

        try:
            if not self._skip_rest:
                super().preprocess_cell(cell, resources, index)  # type: ignore
        except CellExecutionError as e:
            self.failing_cell_index = index
            if self.tear_down_cells:
                print(f"Error in cell {index} ({describe_error(e)}); running tear down cells", flush=True)
                self.teardown(resources)
            raise e

    def teardown(self, resources: Any) -> None:
        for td_cell, td_idx in self.tear_down_cells:
            try:
                super().preprocess_cell(td_cell, resources, td_idx)  # type: ignore
            except CellExecutionError as td_e:
                print(f"Error running tear down cell {td_idx}: {describe_error(td_e)}", flush=True)


class TearDownCollector(ExecutePreprocessor):
    def __init__(self, **kw: Any):
        super().__init__(**kw)  # type: ignore

    def init_notebook(self) -> None:
        self._tear_down_cells: list[IndexedCell] = []

    def preprocess_cell(self, cell: Any, resources: Any, index: int) -> None:
        if TEARDOWN_CELL_TAG in cell["metadata"].get("tags", []):
            self._tear_down_cells.append(IndexedCell(cell, index))

    def tear_down_cells(self) -> list[IndexedCell]:
        return self._tear_down_cells


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text)


def apply_replacements(nb: Any, replacements: dict[str, str] | None) -> None:
    if not replacements:
        return
    unmatched = set(replacements)
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        for old, new in replacements.items():
            if old in cell.source:
                cell.source = cell.source.replace(old, new)
                unmatched.discard(old)
    if unmatched:
        print(f"Warning: no code cell contained {sorted(unmatched)} to replace", flush=True)


def describe_error(e: CellExecutionError) -> str:
    if e.ename or e.evalue:
        return f"{e.ename}: {strip_ansi(e.evalue)}".strip()
    lines = strip_ansi(str(e)).strip().splitlines()
    return lines[-1] if lines else "unknown error"


def summarize_error(notebook_filename: pathlib.Path, cell_index: int | None, e: CellExecutionError) -> str:
    location = f"cell {cell_index}" if cell_index is not None else "unknown cell"
    cell_frame = CELL_FRAME_RE.search(strip_ansi(str(e)))
    if cell_frame:
        location = f"{location}, {cell_frame.group(0)}"
    return f"{notebook_filename.name} ({location}) failed:\n{describe_error(e)}"


def run_notebooks(notebook_names: list[str], replacements: dict[str, str] | None = None) -> None:
    current_dir = pathlib.Path(__file__).parent.resolve()
    examples_path = current_dir.parent.parent / "examples"

    notebook_files = [
        f for f in examples_path.iterdir() if f.is_file() and f.suffix == ".ipynb" and f.name in notebook_names
    ]

    if not notebook_files:
        raise RuntimeError(f"No matching notebooks found in {examples_path}")

    ep = TeardownExecutePreprocessor(kernel_name="python3")
    td_collector = TearDownCollector(kernel_name="python3")
    error_summaries: list[str] = []

    for notebook_filename in notebook_files:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{now}: Executing notebook {notebook_filename}", flush=True)

        with open(notebook_filename) as f:
            nb = nbformat.read(f, as_version=4)  # type: ignore

            apply_replacements(nb, replacements)

            # Collect tear down cells
            td_collector.init_notebook()
            td_collector.preprocess(nb)

            ep.init_notebook(tear_down_cells=td_collector.tear_down_cells())

            # run the notebook
            try:
                ep.preprocess(nb)
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"{now}: Finished executing notebook {notebook_filename}", flush=True)
            except CellExecutionError as e:
                error_summaries.append(summarize_error(notebook_filename, ep.failing_cell_index, e))
                continue

    if error_summaries:
        summary = "\n\n".join(error_summaries)
        pluralized = "errors" if len(error_summaries) > 1 else "error"
        raise RuntimeError(f"{len(error_summaries)} {pluralized} occurred while executing notebooks:\n\n{summary}")
    else:
        print("Finished executing notebooks", flush=True)
