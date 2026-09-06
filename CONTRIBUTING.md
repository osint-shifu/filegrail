# Contributing

Contributions are welcome.

## Development setup

```bash
git clone https://github.com/osint-shifu/filegrail.git
cd filegrail

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

python -m pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
```

`filegrail` has **no runtime dependencies** and that is a deliberate constraint,
not an accident. A change that adds one has to earn it; so far everything,
including the CBOR decoder needed for C2PA, has been reachable with the standard
library.

## Adding an evidence source

An evidence source produces one or more evidence records from an artifact, a
metadata block, an application database, a filesystem attribute or another
supported store. It does not have to answer "where did this come from" - EXIF
and Recent Documents are sources too, and they answer different questions.

Say five things about a new one, in code and in the tables it registers with:

| | |
|:---|:---|
| **category** | `origin`, `metadata` or `activity`, in `models.SOURCE_CATEGORIES`. `category()` raises for a source that is in neither table, on purpose: the old default classified by forgetting. |
| **source** | The artifact or block the record came from, named the way an analyst names it - `Chromium download history`, `Zone.Identifier`, `EXIF`. Not a person, a camera or a cluster key. |
| **match basis** | How the record was tied to *this* file, in `models.SOURCE_MATCH` or on the record. A path, a name, a name and size, membership of a container, or the file's own bytes. Where the tie is not direct, the record carries it. |
| **data produced** | The fields the record fills in, and nothing inferred from elsewhere. If a field is absent, leave it absent. |
| **limitations** | What the record cannot establish. A sync folder does not say which way the bytes travelled; a file name in a messenger's pattern is an association with a naming convention. |

Two more rules, unchanged:

- **Fail quietly when absent.** A missing profile, an unreadable file or a
  malformed container is ordinary, not an error. One bad file must never end a
  scan.
- **Never write.** The tool reads. It does not modify files, profiles or
  histories, and a live database is copied before being opened.

There is a presentation order in `models.SOURCE_PRIORITY`, used to decide which
record a one-row summary shows. It is not a confidence, it is never printed and
it is never exported. Do not reach for it to express how much a source is worth
believing - that is what the category and the match basis are for.

## Adding a format

Metadata is the substance of this tool, so a format that carries any is worth
reading. Put the reader in `src/filegrail/sources/embedded/`, one module per
container family, and add a test that builds a minimal valid file rather than
committing a sample.

Do not compute byte lengths by hand in a test. Encode the structure with a small
helper instead, so a miscounted length cannot silently produce a passing test on
malformed input.

Add the format to the table in [`FORMATS.md`](docs/FORMATS.md) in the same change.
That file is parsed by `tests/test_documented_formats.py` and held against the
readers, so a format you can read and did not document is a failing test rather
than a document that quietly stops being true.

Build the fixture the way a real encoder writes the file, not the way the
specification reads. The two differ, and where they differ is where the bugs
are: a HEIC names an `Exif` item in its item table long before the payload
appears, so a reader that stops at the first marker decodes the table and
reports nothing — on a green suite, because no synthetic fixture had a table.

## The local corpus

`tests/test_corpus.py` reads whatever real files you have put in `test-data/`,
which is deliberately not committed. It asserts one invariant: a file holding a
payload the TIFF parser can decode must not come back empty. That catches the
class of bug a synthetic fixture cannot, without third-party binaries entering
the tree.

It skips when the directory is absent, so it is a local net rather than a CI
gate. Point it at a directory of real photographs and documents before sending a
change that touches a reader.

## Pull requests

Keep changes focused and include tests for behaviour changes.

Priorities, in order: correctness, honesty about what a source does and does not
prove, privacy, portability, and only then breadth.

Commit messages describe what changed and why, in prose. No trailers.
