# whence

Reconstruct where the files in a directory came from — **after** you collected them.

```bash
whence ./case-folder/
```

```text
repro-starter.zip
  <- https://chatgpt.com/backend-api/estuary/content?id=file_00000000…&fn=repro-starter.zip
     browser-download / brave  2026-08-31T10:49:33Z  confidence 90

evidence/photo.jpg
  <- https://forum.example.org/thread/2211/photo.jpg
     browser-download / firefox  2026-08-24T19:02:11Z  confidence 90

metadata.json
  <- exiftool -json evidence/photo.jpg > metadata.json
     shell-history / exiftool  2026-08-24T19:06:40Z  confidence 40

No recorded origin (1):
  notes.md    created 2026-08-24T19:31:08Z

3 of 4 files have a recorded origin.
```

> [!IMPORTANT]
> **Status: working alpha.** Everything documented below is implemented and tested.
> Nothing is documented that does not exist. See [Coverage](#coverage) for the
> honest limits of each source.

---

## Why

Provenance tools normally ask you to wrap every command you run:

```bash
sometool run --input a.jpg --output b.json -- exiftool -json a.jpg
```

Under time pressure, nobody does this. The discipline is abandoned in week two
and the provenance is lost anyway.

`whence` inverts the trade. It asks for nothing up front. It reads records the
operating system, your browser and your shell **already wrote** while you worked
normally, and assembles them into one answer:

> Where did each of these files come from, and when?

It works the first time you run it, on a folder you made last month.

## Install

Python 3.10 or newer. No runtime dependencies.

```bash
pipx install git+https://github.com/OWNER/whence
```

Or run it straight from a checkout:

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

## Where the answers come from

| Source | What it gives | Confidence |
| --- | --- | --- |
| Browser download history | originating page, referrer, redirect chain, timestamp, byte count | 90 |
| Windows `Zone.Identifier` ADS | `HostUrl`, `ReferrerUrl`, zone | 85 |
| macOS `kMDItemWhereFroms` | URL and referrer | 85 |
| Linux `user.xdg.origin.url` | URL and referrer | 80 |
| Archive membership | the origin of the archive a file was extracted from | 70 |
| Shell history | the command that mentions the file | 40 |
| Filesystem | creation and modification time | 10 |

When sources disagree, the highest-confidence one is shown; `--verbose` shows
them all. Shell history never overrides a browser or operating-system record,
because a command naming a file proves it touched the file, not that it produced it.

Browser profiles are **copied before being read**, so a running browser is
neither disturbed nor modified.

## Coverage

The honest version, because this determines whether the tool is useful to you:

| Platform | Reality |
| --- | --- |
| **Browser downloads** | Strongest source everywhere. Chromium-family (Chrome, Brave, Edge, Chromium, Vivaldi) and Firefox. Survives the file being moved or renamed — a name match is reported and flagged as such. |
| **Windows** | `Zone.Identifier` is written for essentially every browser download. Excellent coverage. |
| **macOS** | `kMDItemWhereFroms` is written by Safari and Chrome. Good coverage. |
| **Linux** | `user.xdg.origin.url` is written by KDE tools and by `wget --xattr`, but **not** by Firefox ([Bugzilla 665531](https://bugzilla.mozilla.org/show_bug.cgi?id=665531)), and not by default by most tools. On a sample of 107 files in a real Linux `Downloads` folder, **zero** carried the attribute. Treat it as a bonus, not a source. |
| **Archives** | Files extracted from a downloaded `.zip`/`.tar` inherit its origin, matched on member name and uncompressed size. A member edited after extraction no longer matches — which is itself a useful signal. |
| **Shell history** | Timestamps exist only if the shell was configured for them (`HISTTIMEFORMAT` for bash, `EXTENDED_HISTORY` for zsh). Plain bash history has none, so only ordering survives. |
| **Creation time** | Read via `statx(2)` on Linux, `st_birthtime` on macOS and Windows. Absent on some filesystems. |

## What this is not

- Not a disk-image forensic suite. Point it at a working directory, not a drive.
- Not a chain of custody. It reports what local records say; those records are
  writable by anyone with access to the machine.
- Not proof. A recorded origin is evidence, not a guarantee. Read the confidence.
- Not a collector. It reads; it never writes to your files or profiles.

## Privacy

`whence` runs entirely locally and makes no network requests. It reads browser
history databases and shell history, which are sensitive: the JSON output can
contain URLs you visited and commands you ran. Review before sharing it.

## Contributing

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
ruff check .
```

New sources are welcome. The bar: a source must report what it actually knows,
carry a confidence that reflects its reliability, and fail quietly when absent.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).

> **You already left a trail. `whence` reads it back.**
