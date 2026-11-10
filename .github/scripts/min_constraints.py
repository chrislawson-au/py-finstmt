"""Pin every runtime dependency in pyproject.toml to its declared lower bound.

The min-versions CI job installs finstmt with these pip constraints, so the
lower bounds are tested rather than just declared. Fails if a runtime
dependency has no ">=" lower bound.

Usage: python min_constraints.py [pyproject.toml] > constraints.txt
"""

import re
import sys
import tomllib
from pathlib import Path


def lower_bound_pins(pyproject_text: str) -> list[str]:
    dependencies = tomllib.loads(pyproject_text)["tool"]["poetry"]["dependencies"]
    pins = []
    for name, spec in dependencies.items():
        if name == "python":
            continue
        if isinstance(spec, dict):
            if spec.get("optional"):
                continue
            spec = spec["version"]
        match = re.fullmatch(r">=\s*([0-9][0-9A-Za-z.]*)", spec.strip())
        if match is None:
            raise SystemExit(f"{name}: expected a '>=X' lower bound, got {spec!r}")
        pins.append(f"{name}=={match.group(1)}")
    return pins


if __name__ == "__main__":
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "pyproject.toml")
    print("\n".join(lower_bound_pins(path.read_text())))
