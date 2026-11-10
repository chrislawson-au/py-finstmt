"""Run every ```python block in the repo's Markdown docs, in order.

Blocks fenced as ```py are illustrations (for example 1.x code) and are not
run. Blocks of one document share a namespace and run from the repo root, so
later examples can build on earlier ones and use the sample data in tests/.
"""

import re
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[2]
PYTHON_BLOCK = re.compile(r"^```python\n(.*?)^```", re.S | re.M)


@pytest.mark.parametrize("doc", ["README.md", "MIGRATION.md"])
def test_python_examples_run(doc, monkeypatch):
    path = ROOT / doc
    if not path.exists():
        pytest.skip(f"{doc} is not available (installed-wheel run or not written yet)")
    blocks = PYTHON_BLOCK.findall(path.read_text())
    assert blocks, f"{doc} has no runnable ```python examples"
    monkeypatch.chdir(ROOT)
    namespace: dict = {"__name__": "__docs__"}
    for number, block in enumerate(blocks, start=1):
        exec(compile(block, f"{doc} example {number}", "exec"), namespace)
