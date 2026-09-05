"""Reading an extended attribute on a platform that keeps them.

`os.getxattr` is a Linux interface: the standard library does not expose the
call on macOS at all. Everything here that reads an attribute was guarded with
`hasattr(os, "getxattr")` and therefore did nothing on macOS - including the
macOS where-from attribute, which is the one thing that guard exists for. The
tool said so honestly in `doctor` and read nothing regardless.

These run wherever an attribute can be written, so the Linux path is checked
here and the Darwin path is checked on a macOS runner. Windows has no such
interface and skips.
"""

from __future__ import annotations

import plistlib
from pathlib import Path

import pytest

from filegrail.sources.fsattrs import read_file_attributes
from filegrail.util import read_xattr, xattrs_readable
from tests.xattrs import supported, write

WHERE_FROM = "com.apple.metadata:kMDItemWhereFroms"


@pytest.fixture
def target(tmp_path: Path) -> Path:
    path = tmp_path / "downloaded.bin"
    path.write_bytes(b"bytes")
    return path


def _set(path: Path, name: str, value: bytes) -> None:
    if not supported():
        pytest.skip("no interface for extended attributes on this platform")
    if not write(path, name, value):
        pytest.skip("this filesystem refuses extended attributes")


def test_an_attribute_written_here_can_be_read_back(target: Path):
    _set(target, "user.filegrail.probe", b"a value")

    assert read_xattr(target, "user.filegrail.probe") == b"a value"


def test_an_attribute_that_is_not_there_reads_as_nothing(target: Path):
    if not supported():
        pytest.skip("no interface for extended attributes on this platform")

    assert read_xattr(target, "user.filegrail.absent") is None


def test_a_file_that_is_not_there_reads_as_nothing(tmp_path: Path):
    assert read_xattr(tmp_path / "nowhere", "user.filegrail.probe") is None


def test_the_platform_says_whether_it_keeps_attributes_at_all():
    """`doctor` turns on this, so it must not be a guess about the module."""
    assert xattrs_readable() == supported()


def test_a_macos_where_from_attribute_is_read_where_one_can_be_written(target: Path):
    """The attribute this whole interface exists for.

    On Linux the name lives in the user namespace, which is where a copied
    macOS volume carries it; on macOS it is written under its own name. Either
    way the reader has to come back with the URL.
    """
    from filegrail.sources.fsattrs import _MACOS_WHEREFROMS

    plist = plistlib.dumps(["https://cdn.example.org/a.zip", "https://example.org/page"])
    for name in (_MACOS_WHEREFROMS, f"user.{_MACOS_WHEREFROMS}"):
        if write(target, name, plist):
            break
    else:
        pytest.skip("no extended attribute could be written here")

    origins = read_file_attributes(target)

    found = [origin for origin in origins if origin.source == "macos-wherefroms"]
    assert found, [origin.source for origin in origins]
    assert found[0].url == "https://cdn.example.org/a.zip"
    assert found[0].referrer == "https://example.org/page"
