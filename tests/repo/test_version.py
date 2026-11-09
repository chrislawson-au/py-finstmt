"""The package version is declared in pyproject.toml and finstmt/__init__.py
(semantic-release updates both). Keep them, and installed metadata, in step."""

import tomllib
from importlib import metadata
from pathlib import Path

import pytest
from packaging.version import Version

import finstmt

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_version_matches_pyproject():
    if not PYPROJECT.exists():
        pytest.skip("pyproject.toml is not available (installed-wheel run)")
    declared = tomllib.loads(PYPROJECT.read_text())["tool"]["poetry"]["version"]
    assert Version(finstmt.__version__) == Version(declared)


def test_version_matches_installed_metadata():
    try:
        installed = metadata.version("finstmt")
    except metadata.PackageNotFoundError:
        pytest.skip("finstmt is not installed (source checkout on PYTHONPATH)")
    assert Version(finstmt.__version__) == Version(installed)
