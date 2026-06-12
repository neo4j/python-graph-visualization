from tests.notebook_runner import run_notebooks


def test_simple() -> None:
    run_notebooks(["getting-started.ipynb"])
