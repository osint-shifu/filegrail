"""What the distribution says it is, held against what it actually contains.

Nothing here exercises the tool. These are the statements a package makes about
itself to people who will never read its code - an installer, a licence
scanner, a lawyer clearing it for use in a case - and each one is made in more
than one place, so each one can drift.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: sha256 of the Apache License, Version 2.0 exactly as apache.org publishes it
#: at https://www.apache.org/licenses/LICENSE-2.0.txt. The text is frozen, so
#: this is a constant and not a moving target.
APACHE_2_0 = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"


def _licence_digest(path: Path) -> str:
    """Which licence this is, independent of how a checkout spells its newlines.

    Git gives a Windows clone the same licence with CRLF, which changes every
    byte of the hash and nothing about the licence. Normalising first is what
    keeps this a question about the text.
    """
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_the_licence_file_is_the_licence_the_package_declares():
    """One licence stated twice, the way the version is stated twice.

    `pyproject.toml`, the README badge and the metadata on PyPI all say
    Apache-2.0. The file under that name has to be that licence and not a
    paraphrase of it, and the difference is not cosmetic: a reflowed or
    shortened copy is not recognised, so GitHub reports the repository as
    carrying no licence at all and every scanner that keys off the text agrees
    with it. Section 4 of the licence also asks that recipients be given a copy
    of *the* Licence, which a copy with clauses missing from it is not.
    """
    pyproject = (ROOT / "pyproject.toml").read_text("utf-8")
    declared = re.search(r'(?m)^license = \{ text = "([^"]+)" \}$', pyproject)

    assert declared is not None, "pyproject.toml no longer declares its licence on one line"
    assert declared.group(1) == "Apache-2.0"

    assert _licence_digest(ROOT / "LICENSE") == APACHE_2_0, (
        "LICENSE is not the text apache.org publishes. Restore it verbatim from "
        "https://www.apache.org/licenses/LICENSE-2.0.txt; it is not a document to edit."
    )


def test_a_windows_checkout_of_the_licence_is_the_same_licence(tmp_path: Path):
    """Git hands a Windows clone the same file with CRLF, and it is the same file.

    This is what the byte hash above got wrong on its first outing: it pinned
    the licence together with the line endings the machine that cloned it
    happens to prefer, and the Windows runners rejected a licence that was
    letter perfect.
    """
    windows = tmp_path / "LICENSE"
    windows.write_bytes((ROOT / "LICENSE").read_bytes().replace(b"\n", b"\r\n"))

    assert _licence_digest(windows) == APACHE_2_0


def test_a_licence_that_is_not_the_apache_one_is_still_rejected(tmp_path: Path):
    """Normalising line endings must not turn the check into a formality."""
    other = tmp_path / "LICENSE"
    other.write_text("MIT License\n\nPermission is hereby granted...\n", encoding="utf-8")

    assert _licence_digest(other) != APACHE_2_0
