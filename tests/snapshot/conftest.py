import importlib.util
from typing import Optional

import pytest
from syrupy import SnapshotAssertion
from syrupy.extensions.amber import AmberDataSerializer
from syrupy.extensions.single_file import SingleFileSnapshotExtension, WriteMode
from syrupy.types import (
    PropertyFilter,
    PropertyMatcher,
    SerializableData,
    SerializedData,
)

from tests.snapshot.ext_prettyprinter.dataclasses import (
    install as install_custom_dataclass_prettyprinter_extension,
)

install_custom_dataclass_prettyprinter_extension()


def pytest_configure(config):
    # Without prophet the prophet-only forecast tests skip, so their snapshots go
    # unused, and syrupy cannot tie single-file snapshots to skipped tests. Only
    # then, report unused snapshots as a warning instead of failing the session.
    if importlib.util.find_spec("prophet") is None:
        config.option.warn_unused_snapshots = True


class SingleFileTextSnapshotExtension(SingleFileSnapshotExtension):
    _write_mode = WriteMode.TEXT
    # syrupy < 5 reads _file_extension; syrupy >= 5 renamed it to file_extension
    _file_extension = "txt"
    file_extension = "txt"

    def serialize(
        self,
        data: "SerializableData",
        *,
        exclude: Optional["PropertyFilter"] = None,
        matcher: Optional["PropertyMatcher"] = None,
        **kwargs,
    ) -> "SerializedData":
        return AmberDataSerializer.serialize(data, exclude=exclude, matcher=matcher)


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion):
    return snapshot.use_extension(SingleFileTextSnapshotExtension)
