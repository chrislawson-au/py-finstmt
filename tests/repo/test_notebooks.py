"""Committed example notebooks carry no outputs, so the repo stays small and
diffs stay readable. CI executes them separately (compat.yml: notebooks)."""

import json
from pathlib import Path

import pytest

NOTEBOOKS = sorted((Path(__file__).resolve().parents[2] / "nbexamples").glob("*.ipynb"))


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda path: path.name)
def test_notebook_has_no_outputs(path):
    notebook = json.loads(path.read_text())
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            assert (
                cell["outputs"] == []
            ), f"{path.name}: clear outputs before committing"
            assert (
                cell["execution_count"] is None
            ), f"{path.name}: clear execution counts"
