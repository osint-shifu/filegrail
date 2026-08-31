# whence

Reconstruct where the files in a directory came from — **after** you collected them.

```bash
whence ./case-folder/
```

```text
evidence/photo.jpg
  <- https://forum.example.org/thread/2211/photo.jpg
     browser-download / firefox  2026-08-24T19:02:11Z  confidence 90

toolkit/parser.py
  <- https://example.org/releases/toolkit-2.4.zip
     archive-member / brave  2026-08-24T18:55:02Z  confidence 70
     note      extracted from toolkit-2.4.zip

metadata.json
  <- exiftool -json evidence/photo.jpg > metadata.json
     shell-history / exiftool  2026-08-24T19:06:40Z  confidence 40

No recorded origin (1):
  notes.md    created 2026-08-24T19:31:08Z

3 of 4 files have a recorded origin.
```

> [!IMPORTANT]
> **Status: working alpha.** Everything documented here is implemented and tested.
> Nothing is documented that does not exist.

---

## Why

Provenance tools normally ask you to wrap every command you run:

```bash
sometool run --input a.jpg --output b.json -- exiftool -json a.jpg
```

Under time pressure, nobody does this. The discipline is abandoned in week two
and the provenance is lost anyway.

`whence` inverts the trade. It asks for nothing up front. It reads records your
operating system, browser and shell **already wrote** while you worked normally,
and assembles them into one answer:

> Where did each of these files come from, and when?

It works the first time you run it, on a folder you made last month.

## Install

Python 3.10 or newer. No runtime dependencies.

```bash
pipx install git+https://github.com/OWNER/whence
```

Or run it from a checkout:

```bash
PYTHONPATH=src python -m whence.cli ./case-folder/
```

## Usage

```bash
whence                       # current directory
whence ./case-folder/        # one directory, recursively
whence report.pdf            # a single file
whence . --verbose           # every origin claim, not just the strongest
whence . --timeline          # chronological, one line per event
whence . --json              # machine-readable
whence . --unknown-only      # only files with no recorded origin
whence . --hash              # add SHA-256 for each file
whence . --no-shell-history  # skip shell correlation
whence . --no-archives       # do not inherit origins from archives
```

## Sources

Confidence reflects how much a source is trusted when several disagree. The
highest wins; `--verbose` shows them all.

| Source | What it gives | Conf. | Coverage in practice |
| --- | --- | :-: | --- |
| Browser downloads | originating page, referrer, redirect chain, timestamp, size | 90 | Strongest source on every platform. Chromium-family (Chrome, Brave, Edge, Vivaldi) and Firefox. Survives a file being moved or renamed — the name match is flagged as such. |
| Windows `Zone.Identifier` | `HostUrl`, `ReferrerUrl`, zone | 85 | Written for essentially every browser download. Excellent. |
| macOS `kMDItemWhereFroms` | URL and referrer | 85 | Written by Safari and Chrome. Good. |
| Linux `user.xdg.origin.url` | URL and referrer | 80 | Written by KDE tools and `wget --xattr`, but **not** by Firefox ([Bugzilla 665531](https://bugzilla.mozilla.org/show_bug.cgi?id=665531)). On a sample of 107 files in a real Linux `Downloads` folder, **zero** carried it. A bonus, not a source. |
| Archive membership | the origin of the archive a file came out of | 70 | Members matched on name and uncompressed size, so an unpacked download does not lose its provenance. |
| Shell history | the command that mentions the file | 40 | Never overrides a browser or OS record: a command naming a file proves it touched the file, not that it produced it. Timestamps only if the shell stored them (`HISTTIMEFORMAT`, `EXTENDED_HISTORY`). |
| Filesystem | creation and modification time | 10 | Creation time via `statx(2)` on Linux, `st_birthtime` elsewhere. Absent on some filesystems. |

Browser profiles are **copied before being read**, so a running browser is
neither disturbed nor modified.

## What this is not

- Not a disk-image forensic suite. Point it at a working directory, not a drive.
- Not a chain of custody. It reports what local records say, and those records
  are writable by anyone with access to the machine.
- Not proof. A recorded origin is evidence. Read the confidence.
- Not a collector. It reads; it never writes to your files or profiles.

## Privacy

`whence` runs entirely locally and makes no network requests. It reads browser
and shell history, so its output can contain URLs you visited and commands you
ran. Review before sharing it.

## Contributing

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
ruff check .
```

New sources are welcome. The bar: report only what the source actually knows,
carry a confidence that reflects its reliability, and fail quietly when absent.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).

> **You already left a trail. `whence` reads it back.**
