import importlib.util

import pytest

requires_prophet = pytest.mark.skipif(
    importlib.util.find_spec("prophet") is None,
    reason="needs the optional prophet dependency: pip install 'finstmt[forecast]'",
)
