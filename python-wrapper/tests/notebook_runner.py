import pathlib
import signal
import sys
from datetime import datetime
from typing import Any, NamedTuple

import nbformat
from nbclient.exceptions import CellExecutionError
from nbconvert.preprocessors.execute import ExecutePreprocessor

TEARDOWN_CELL_TAG = "teardown"


class IndexedCell(NamedTuple):
    cell: Any
    index: int  # type: ignore


class TeardownExecutePreprocessor(ExecutePreprocessor):
    def __init__(self, **kw: Any):
        super().__init__(**kw)  # type: ignore

    def init_notebook(self, tear_down_cells: list[IndexedCell]) -> None:
        self.tear_down_cells = tear_down_cells
        self._skip_rest = False

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
            if self.tear_down_cells:
                print(f"Running tear down cells due to error in notebook execution: {e}")
                self.teardown(resources)
            raise e

    def teardown(self, resources: Any) -> None:
        for td_cell, td_idx in self.tear_down_cells:
            try:
                super().preprocess_cell(td_cell, resources, td_idx)  # type: ignore
            except CellExecutionError as td_e:
                print(f"Error running tear down cell {td_idx}: {td_e}")


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


def run_notebooks(notebook_names: list[str]) -> None:
    current_dir = pathlib.Path(__file__).parent.resolve()
    examples_path = current_dir.parent.parent / "examples"

    notebook_files = [
        f for f in examples_path.iterdir() if f.is_file() and f.suffix == ".ipynb" and f.name in notebook_names
    ]

    if not notebook_files:
        raise RuntimeError(f"No matching notebooks found in {examples_path}")

    ep = TeardownExecutePreprocessor(kernel_name="python3")
    td_collector = TearDownCollector(kernel_name="python3")
    exceptions: list[RuntimeError] = []

    for notebook_filename in notebook_files:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{now}: Executing notebook {notebook_filename}", flush=True)

        with open(notebook_filename) as f:
            nb = nbformat.read(f, as_version=4)  # type: ignore

            # Collect tear down cells
            td_collector.init_notebook()
            td_collector.preprocess(nb)

            ep.init_notebook(tear_down_cells=td_collector.tear_down_cells())

            # run the notebook
            try:
                ep.preprocess(nb)
                print(f"Finished executing notebook {notebook_filename}")
            except CellExecutionError as e:
                exceptions.append(RuntimeError(f"Error executing notebook {notebook_filename}", e))
                continue

    if exceptions:
        for nb_ex in exceptions:
            print(nb_ex)
        raise RuntimeError(f"{len(exceptions)} Errors occurred while executing notebooks")
    else:
        print("Finished executing notebooks")
