import pytest

from tests.notebook_runner import run_notebooks


@pytest.mark.requires_snowflake
def test_snowflake() -> None:
    run_notebooks(["snowflake-example.ipynb"])
