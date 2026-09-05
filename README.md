<div align="center">

# FileGrail

### Reconstruct how files arrived. Extract what they reveal.

**Local file provenance and metadata analysis for OSINT, DFIR, investigations and research.**

[![PyPI](https://img.shields.io/pypi/v/filegrail?style=flat-square&color=3775A9)](https://pypi.org/project/filegrail/)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square)
![Runtime dependencies](https://img.shields.io/badge/runtime_dependencies-0-1f883d?style=flat-square)
![Local and read-only](https://img.shields.io/badge/local_%26_read--only-yes-1f883d?style=flat-square)
![Network requests](https://img.shields.io/badge/network_requests-none-1f883d?style=flat-square)
[![CI](https://github.com/osint-shifu/filegrail/actions/workflows/ci.yml/badge.svg)](https://github.com/osint-shifu/filegrail/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-Apache--2.0-8250df?style=flat-square)

[Why FileGrail?](#why-filegrail) ·
[Features](#features) ·
[Install](#installation) ·
[Usage](#usage) ·
[Examples](#practical-examples) ·
[Formats](#supported-formats) ·
[JSON](#json-and-automation)

</div>

---

## Why FileGrail?

Metadata tools answer questions like:

> Who created this file? Which camera took this photo? What software edited this document?

During an investigation that is half the problem. You also need to know:

> **How did this file reach the machine? Where was it downloaded from? Was it extracted from an archive, or listed in a torrent? What touched it afterwards? Do its own metadata blocks contradict each other? Is it related to another file in the same directory?**

**FileGrail reads file metadata and surviving local provenance evidence in one pass, and keeps them apart.**

> [!IMPORTANT]
> FileGrail works **after the fact**. No monitoring agent, provenance database, browser extension or prior setup has to exist before the file appears.

```text
file
├── acquisition   how it reached the machine
├── intrinsic     what the file says about its earlier life
└── interaction   what touched it after arrival
```

Rather than flattening everything into one vague "origin" field, FileGrail keeps those classes separate and reports what each source actually supports.

---

## Features

### Trace how a file arrived

Evidence the system and its applications already left behind:

- browser download history
- Windows `Zone.Identifier`
- macOS where-from and quarantine records
- Linux XDG origin attributes
- archive membership, with the archive's own origin inherited
- torrent membership, from the scanned tree and from local client stores
- `yt-dlp` `.info.json` sidecars
- shell history
- sync client folders — Nextcloud, Dropbox, Syncthing, OneDrive
- messaging-client filename patterns

### Extract metadata

- EXIF, XMP and XMP editing history, IPTC
- C2PA Content Credentials
- PDF, Microsoft Office and OpenDocument properties
- image, audio and video container metadata
- email headers and every delivery hop
- files **inside** archives, read without unpacking them
- EPUB, RTF, SVG and notebook metadata

Decoded fields stay visible rather than being narrowed to whichever one looks interesting.

### Correlate and contradict

FileGrail does more than extract:

- corroboration between independent acquisition records, and conflicting origin URLs
- size mismatches and filename-only matches
- **impossible ordering** — a document modified before it was created, or an editing history recorded out of the sequence it lists
- mirrored metadata blocks held against each other, such as EXIF against XMP or a PDF `Info` dictionary against XMP
- XMP derivation chains between files in the same scan
- the C2PA **hard binding** recomputed against the file, so a manifest carried by different bytes is reported

### Investigation pivots

`--identify` extracts values from decoded metadata while preserving the file and field they came from: URLs, domains, email addresses, IPv4 addresses, coordinates, and hashes under their own algorithm (`md5`, `sha1`, `sha256`).

### Shared sources

`--cluster` reduces a directory to the sources behind it, on three axes kept deliberately apart: a **camera body** (one physical device, by serial), a **camera model** (a product thousands of people own — not the same claim) and an **author** (a name, as somebody typed it).

### Remove metadata

`filegrail clean` writes copies of files with their metadata taken out — JPEG, PNG, MP4/MOV and the zip-based Office and OpenDocument formats. It reuses `--type` and `--ext`, so a directory can be cleaned one format at a time.

> [!IMPORTANT]
> **The original is never touched.** Copies go to `--out`, which must be outside the directory being read. Every copy is then read back with the same readers that find metadata in the first place, and anything still visible is reported rather than hidden — because somebody is about to publish a file on the strength of the word *cleaned*.

Removing the fields is removing the fields: pixels still carry sensor noise, an encoder still leaves its own fingerprints. This is not an anonymiser.

### Timelines

`--timeline` places acquisition, creation, editing and interaction events in chronological order.

### Another user profile

`--home` points the same readers at a copied or mounted profile. A Windows browser profile can be examined while FileGrail runs on Linux.

### Evidence coverage

`filegrail doctor` reports which sources are actually available and, where possible, how far back they reach.

> [!NOTE]
> *The evidence was searched and the file was not in it* is a finding. *The evidence was never there to search* is not a finding about the file at all. A report cannot tell those apart on its own, so `doctor` says up front which one you are looking at.

---

## Installation

Requires **Python 3.10+**.

```bash
pipx install filegrail
```

```bash
uv tool install filegrail
```

From a checkout:

```bash
git clone https://github.com/osint-shifu/filegrail.git
cd filegrail
PYTHONPATH=src python -m filegrail.cli /path/to/files
```

Runtime dependencies: **zero**.

---

## Usage

```text
filegrail <path> [options]
filegrail <command> [options]
```

A path can be one file or a whole directory; with no path, the current directory.

```bash
filegrail suspicious.pdf
filegrail ./evidence
```

### Commands

| Command | What it does |
| :--- | :--- |
| `filegrail PATH` | Scan a file or directory |
| `filegrail explain FILE` | Show every source behind the findings for one file |
| `filegrail compare A B` | Compare metadata, provenance and timing |
| `filegrail doctor` | Show which local evidence sources are available |
| `filegrail clean PATH --out DIR` | Write copies with the metadata removed |
| `filegrail menu` | Open the interactive menu |
| `filegrail help COMMAND` | Show help for one command |

### Scan options

| Option | Purpose |
| :--- | :--- |
| `-v`, `--verbose` | Every evidence record, not the strongest of each kind |
| `--brief` | Summarise each file instead of listing every field |
| `--timeline` | One chronological line per event |
| `--identify` | Extract investigation pivots from metadata |
| `--cluster` | Group files by the sources more than one of them names |
| `--unknown-only` | Only files nothing was found for |
| `--hash` | Compute SHA-256 for each file |
| `-j`, `--json` | Machine-readable output |
| `--redact` | Redact credentials before printing |
| `--type NAME` | One family: `archive`, `audio`, `document`, `image`, `mail`, `text`, `video` |
| `--ext LIST` | Only these extensions, e.g. `--ext jpg,pdf` |
| `--limit N` | Cap the list of files with no findings; `0` for all |
| `--home DIR` | Read local evidence from another user profile |
| `--no-recurse` | Do not descend into subdirectories |
| `--no-shell-history` | Skip shell-history correlation |
| `--no-archives` | Do not read archives or inherit their origins |
| `--no-color` | Disable ANSI colour |

```bash
filegrail help scan
```

gives the complete reference.

---

## Practical examples

### One file

```bash
filegrail holiday.jpg
```

```text
● holiday.jpg                                                   3.4 MB
← https://portal.example.org/press/holiday.jpg
│ browser download · firefox · 2026-08-24T19:02:11Z
│
← made by NIKON COOLPIX P6000
│ device metadata · 2008-10-22T16:28:39Z
│ geo       43.467448, 11.885127
│
├ Make               NIKON
├ Model              COOLPIX P6000
├ BodySerialNumber   3001234
└ DateTimeOriginal   2008:10:22 16:28:39
```

The browser record says **how the bytes reached the machine**. The EXIF block describes **the image before that**. Both stay.

### A directory

```bash
filegrail ./case-files
```

Scans recursively and leads with an overview before the per-file results.

### Files nothing explains

```bash
filegrail ./case-files --unknown-only
```

`no findings` means exactly that: no acquisition record, no metadata, and nothing on this machine that touched the file. It does not mean the file appeared from nowhere.

### Pivots, clusters and timelines

```bash
filegrail ./case-files --identify
filegrail ./case-files --cluster
filegrail ./case-files --timeline
```

### Explain one result

```bash
filegrail explain statement.pdf
```

Use it when the summary is not enough and you want every source, including the ones that disagree.

### Compare two files

```bash
filegrail compare original.jpg edited.jpg
```

Exposes shared device metadata, creation context and timing, and differences in how each file arrived.

### Another profile, JSON, redaction

```bash
filegrail /mnt/case/files --home /mnt/case/Users/Alice
filegrail /mnt/evidence --hash --json > filegrail.json
filegrail . --redact --json > report.json
```

---

## How FileGrail reasons about evidence

Every result is a claim from one source. A browser database, an EXIF block, a shell command, an XMP packet, a torrent and a recent-document record do not prove the same thing and are not presented as though they do.

| Class | Question | Examples |
| :--- | :--- | :--- |
| **Acquisition** | How did the file reach this machine? | Browser downloads, OS origin metadata, archives, torrents, download sidecars, fetch commands |
| **Intrinsic** | What does the file reveal about its earlier life? | EXIF, XMP, IPTC, C2PA, document and media metadata, archive contents |
| **Interaction** | What touched it after arrival? | Recent documents, shortcuts, sync folders, non-fetch shell commands |

Agreement between independent sources is reported as corroboration. Disagreement is reported as a conflict rather than resolved silently.

> [!NOTE]
> **A conflict is evidence too.** FileGrail shows the disagreement and the sources behind it instead of quietly printing the higher-scoring one.

Confidence values rank competing claims of the same kind. They are **not probability scores and not forensic verdicts**.

---

## File relationships

`xmpMM:DocumentID`, `xmpMM:InstanceID`, `xmpMM:OriginalDocumentID` and `xmpMM:DerivedFrom` survive renaming, and link a master, its export and a rendition of that export as *derived from*, *source of*, *same document*, *descends from*, *original of* or *common ancestor*.

A shared **original** is only ever reported as a common ancestor: a template carries its XMP into everything made from it, and those files share an ancestor and nothing else. The reasoning is in [`docs/specs/2026-09-01-derivation-lineage.md`](docs/specs/2026-09-01-derivation-lineage.md).

---

## Supported formats

Readers cover 68 file extensions across the major families.

| Family | Examples |
| :--- | :--- |
| Images | JPEG, TIFF, DNG, NEF, CR2, ARW, WebP, HEIC, AVIF, PNG |
| Documents | PDF, DOC/DOCX, XLS/XLSX, PPT/PPTX |
| OpenDocument | ODT, ODS, ODP, ODG and related |
| Video | MP4, MOV, AVI, Matroska, WebM |
| Audio | MP3, WAV, FLAC, OGG, Opus |
| Email | EML, MSG |
| Archives | ZIP, TAR and compressed TAR variants |
| Other | EPUB, RTF, SVG, IPYNB, `.torrent` |

The readers define what is supported, not this table. The complete matrix is in [`docs/FORMATS.md`](docs/FORMATS.md), which is held against the code by a test and so cannot drift.

A format FileGrail does not understand is reported as not understood — and still takes part in provenance analysis when local evidence about it exists.

---

## JSON and automation

`--json` is available on every command — `filegrail.scan/1`, `filegrail.explain/1`, `filegrail.compare/1` and `filegrail.doctor/1` — and each document names its schema and the version that produced it:

```json
{
  "schema": "filegrail.scan/1",
  "filegrail_version": "0.2.0",
  "root": "/mnt/evidence"
}
```

It preserves file records, acquisition/intrinsic/interaction claims, decoded metadata, sources, confidence values, findings and conflicts, identifiers, shared-source clusters and file relationships.

---

## Privacy and safety

FileGrail runs locally, makes **no network requests** and does not modify what it inspects.

Its output is another matter: local evidence can carry private URLs, credentials, tokens, paths and addresses.

```bash
filegrail . --redact --json > report.json
```

`--redact` removes credentials from URLs, commands and free-text fields while keeping enough structure for repeated values to stay recognisable.

> [!WARNING]
> Redaction is biased towards precision, not towards catching everything. Always review investigation output before sharing it.

---

## Limits

FileGrail can only analyze evidence that still exists. Browser history gets cleared, extended attributes are lost in copies, shell history may carry no timestamps, and some files never had metadata.

It is deliberately **not** proof, **not** chain of custody, **not** a disk-image forensic suite, **not** a monitoring agent.

C2PA manifests are parsed and their hard binding is recomputed against the file, so a manifest describing different bytes is reported. The cryptographic **signature is still not verified** — that needs certificate-chain validation and a trust list. A binding that matches says the manifest is about *these bytes*; it does not say who wrote it or whether to believe them.

Three readers are written from the specification and have never been run against a file the originating software produced: Outlook `.msg` messages, Windows `.lnk` shortcuts, and the `id3 ` chunk a WAV may carry. [`docs/FORMATS.md`](docs/FORMATS.md) names them, and lists what is deliberately not read at all — including the encrypted stores behind messaging apps and Dropbox.

The goal is not to manufacture certainty. It is to show **what survives, where it came from, what it supports, and where it conflicts**.

---

## Development

```bash
git clone https://github.com/osint-shifu/filegrail.git
cd filegrail

python -m venv .venv
source .venv/bin/activate

python -m pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
```

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before adding a reader or changing what a source is taken to prove. [`SECURITY.md`](SECURITY.md) covers what to report privately, and [`CHANGELOG.md`](CHANGELOG.md) carries the history.

---

## License

Apache License 2.0. See [`LICENSE`](LICENSE).

---

<div align="center">

**FileGrail**

*Reconstruct how files arrived. Extract what they reveal.*

Made by [osint-shifu](https://github.com/osint-shifu)

</div>
