"""Check that built wheels contain the whole package and agree on metadata.

Usage: python check_wheel.py WHEEL [WHEEL ...]

Compares requirements after normalizing them, because poetry-core 1.x writes
"pandas (>=2.2)" where poetry-core 2.x writes "pandas>=2.2".
"""

import sys
import zipfile
from email.parser import Parser

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

REQUIRED_FILES = {
    "finstmt/__init__.py",
    "finstmt/py.typed",
    "finstmt/config/statement_config.yaml",
    "finstmt/deals/__init__.py",
}


def inspect(path: str) -> tuple[list[str], SpecifierSet]:
    if not path.endswith("-py3-none-any.whl"):
        sys.exit(f"{path}: expected a pure-Python py3-none-any wheel")
    with zipfile.ZipFile(path) as wheel:
        names = set(wheel.namelist())
        dist_info = next(
            name.split("/")[0] for name in names if name.endswith(".dist-info/METADATA")
        )
        metadata = Parser().parsestr(wheel.read(f"{dist_info}/METADATA").decode())
    unexpected = {name.split("/")[0] for name in names} - {"finstmt", dist_info}
    if unexpected:
        sys.exit(f"{path}: unexpected top-level entries {sorted(unexpected)}")
    missing = REQUIRED_FILES - names
    if missing:
        sys.exit(f"{path}: missing {sorted(missing)}")
    requires = sorted(
        str(Requirement(r)) for r in metadata.get_all("Requires-Dist") or []
    )
    if not any(r.startswith("pandas") for r in requires):
        sys.exit(f"{path}: no runtime dependencies declared")
    return requires, SpecifierSet(metadata["Requires-Python"])


results = {path: inspect(path) for path in sys.argv[1:]}
first_path, first = next(iter(results.items()))
for path, result in results.items():
    if result != first:
        sys.exit(f"metadata differs:\n{first_path}: {first}\n{path}: {result}")
    print(f"ok {path}: Requires-Python {result[1]}, {len(result[0])} requirements")
