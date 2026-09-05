<div align="center">

# filegrail

### Reconstruct how files arrived. Extract what they reveal.

**Local file provenance and metadata analysis for OSINT, DFIR, investigations and research.**

[![PyPI](https://img.shields.io/pypi/v/filegrail?style=flat-square&color=3775A9)](https://pypi.org/project/filegrail/)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square)
![Runtime dependencies](https://img.shields.io/badge/runtime_dependencies-0-1f883d?style=flat-square)
![Local and read-only](https://img.shields.io/badge/local_%26_read--only-yes-1f883d?style=flat-square)
![Network requests](https://img.shields.io/badge/network_requests-none-1f883d?style=flat-square)
[![CI](https://github.com/osint-shifu/filegrail/actions/workflows/ci.yml/badge.svg)](https://github.com/osint-shifu/filegrail/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-Apache--2.0-8250df?style=flat-square)

[Why filegrail?](#why-filegrail) ·
[Features](#features) ·
[Install](#installation) ·
[Usage](#usage) ·
[Examples](#practical-examples) ·
[Formats](#supported-formats) ·
[Full report](#the-whole-report-top-to-bottom) ·
[JSON](#json-and-automation)

</div>

---

## Why filegrail?

Metadata tools answer questions like:

> Who created this file? Which camera took this photo? What software edited this document?

During an investigation that is half the problem. You also need to know:

> **How did this file reach the machine? Where was it downloaded from? Was it extracted from an archive, or listed in a torrent? What touched it afterwards? Do its own metadata blocks contradict each other? Is it related to another file in the same directory?**

**filegrail reads file metadata and surviving local provenance evidence in one pass, and keeps them apart.**

> [!IMPORTANT]
> filegrail works **after the fact**. No monitoring agent, provenance database, browser extension or prior setup has to exist before the file appears.

```text
file
├── acquisition   how it reached the machine
├── intrinsic     what the file says about its earlier life
└── interaction   what touched it after arrival
```

Rather than flattening everything into one vague "origin" field, filegrail keeps those classes separate and reports what each source actually supports.

---

## Features

### Trace how a file arrived

Evidence the system and its applications already left behind:

- browser download history
- Windows `Zone.Identifier`, on Windows and off it — a volume mounted from an image carries the same stream as an extended attribute
- macOS where-from and quarantine records
- Linux XDG origin attributes
- archive membership, with the archive's own origin inherited
- torrent membership, from the scanned tree and from local client stores
- `yt-dlp` `.info.json` sidecars
- shell history
- sync client folders — Nextcloud, Dropbox, Syncthing, OneDrive
- messaging-client filename patterns
- the freedesktop trash — where a deleted file was and when it was thrown away

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

filegrail does more than extract:

- corroboration between independent acquisition records, and conflicting origin URLs
- size mismatches and filename-only matches
- **impossible ordering** — a document modified before it was created, or an editing history recorded out of the sequence it lists
- mirrored metadata blocks held against each other, such as EXIF against XMP or a PDF `Info` dictionary against XMP
- XMP derivation chains between files in the same scan
- the C2PA **hard binding** recomputed against the file, so a manifest carried by different bytes is reported

### Investigation pivots

`--identify` extracts values from decoded metadata while preserving the file and field they came from: URLs, domains, email addresses, IPv4 addresses, coordinates, and hashes under their own algorithm (`md5`, `sha1`, `sha256`).

`--content` widens the corpus from what files record about themselves to what they say — the body of a Word or OpenDocument file, a slide deck, a spreadsheet's strings, HTML, XML, a message body, plain text and data files. **No dependency is added for it**: those formats are zip archives of XML, and filegrail already opens them for their properties. PDF text is deliberately not read: pulling string literals out of a content stream produces readable text for perhaps half of real documents and mush for the rest, and in a tool that reports evidence a confident wrong answer is worse than an absent one. Source code and RTF are left out for reasons of the same kind, written down in `sources/content.py`.

Every value says where in the document it was found, in whatever terms the format actually has: a **line** for text and markup, a **slide**, a **sheet**, a named chapter, the **body** or the **footnotes** of a Word file, the body of a message. A Word file gets no page number, because pagination happens when something renders it and the file does not record where the breaks fell.

The two corpora are kept apart on every value, because prose is an order of magnitude noisier than a property field. That separation is also what makes the interesting answer visible:

> **A value a document names, that the record of the file's arrival also names.** Either alone is ordinary. The two together were put there by separate acts, and only something that already read the arrival record can see it.

### Deleted files

Nothing else on a Linux desktop writes down where a file *used to be*. The freedesktop trash does: the bytes go into `files/` and a record with the same name goes into `info/`, holding the path the file was deleted from and the moment it happened.

```bash
filegrail /mnt/image/home/ann/.local/share/Trash/files
```

```text
  FILES IN DETAIL                                                 1 file
  ──────────────────────────────────────────────────────────────────────

  ● holiday.jpg                                                   3.4 MB

  ACQUISITION  how the file reached this machine
  ← https://portal.example.org/press/2026/holiday-master.jpg
  │ browser download · chromium · 2026-08-31T10:49:33Z      ▰▰▰▰▱ direct
  │ referrer  https://portal.example.org/press/

  INTRINSIC  what the file records about its own earlier life
  ← made by NIKON COOLPIX P6000
  │ device metadata · 2008-10-22T16:28:39Z           ▰▰▰▱▱ self-reported
  │ geo       43.467447, 11.885128
  │
  ├ Make              NIKON
  ├ Model             COOLPIX P6000
  ├ DateTimeOriginal  2008:10:22 16:28:39
  ├ BodySerialNumber  3001234
  ├ GPSLatitudeRef    N
  ├ GPSLatitude       43, 28, 2.81
  ├ GPSLongitudeRef   E
  └ GPSLongitude      11, 53, 6.46
```

The record is found from the file itself, so no `--home` is needed and a trash on a mounted volume reads the same as the desktop's own — including the two per-volume layouts, where the recorded path is relative to the top of that volume.

Two things it is careful about. It is **interaction**, not acquisition: it proves this machine held the file at a path and removed it from there, and says nothing about where the bytes came from before that. And the deletion moment carries **no time zone** — the specification writes the deleting machine's local time and records its offset nowhere — so it is read as UTC and the record keeps the string as written.

### Shared sources

`--cluster` reduces a directory to the sources behind it, on three axes kept deliberately apart: a **camera body** (one physical device, by serial), a **camera model** (a product thousands of people own — not the same claim) and an **author** (a name, as somebody typed it).

### Remove metadata

`filegrail clean` writes copies of files with their metadata taken out — JPEG, PNG, MP4/MOV and the zip-based Office and OpenDocument formats. It reuses `--type` and `--ext`, so a directory can be cleaned one format at a time.

> [!IMPORTANT]
> **The original is never touched.** Copies go to `--out`, which must be outside the directory being read. Every copy is then read back with the same readers that find metadata in the first place, and anything still visible is reported rather than hidden — because somebody is about to publish a file on the strength of the word *cleaned*.

`--check` asks the same question without writing anything: what would come out of each file, and what would a reader still find in the copy. It exits non-zero if any copy would not come out clean, so a directory can be gated before it is published rather than cleaned twice.

Removing the fields is removing the fields: pixels still carry sensor noise, an encoder still leaves its own fingerprints. This is not an anonymiser.

### Timelines

`--timeline` places acquisition, creation, editing and interaction events in chronological order.

### Another user profile

`--home` points the same readers at a copied or mounted profile. A Windows browser profile can be examined while filegrail runs on Linux.

### Evidence coverage

`filegrail doctor` reports which sources are actually available and, where possible, how far back they reach.

> [!NOTE]
> *The evidence was searched and the file was not in it* is a finding. *The evidence was never there to search* is not a finding about the file at all. A report cannot tell those apart on its own, so `doctor` says up front which one you are looking at.

The same rule applies to the directory being scanned. A scan closes by naming every directory it did not look inside, and keeps the two reasons apart: one it **could not read**, and one it **skipped by name** — build output, caches and vendored copies, which bury a report and say nothing about how anything arrived. An evidence directory may perfectly well be called `build`, so the skip is a default rather than a rule about what evidence is, and `--no-skip` turns it off.

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

A path can be one file or a whole directory. `filegrail` with no arguments at all introduces the tool rather than scanning — starting an unasked-for scan of wherever the shell happens to be is a surprise, and in a home directory an expensive one. `filegrail .` scans the current directory, and so does `filegrail scan`.

```bash
filegrail suspicious.pdf
filegrail ./evidence
```

> [!NOTE]
> **A report redirected to a file is laid out for whoever opens it later.** On a terminal filegrail uses the terminal's width; anywhere else it uses 72 columns — what a file survives being quoted in mail, pasted into a ticket, read in a side pane and diffed at. Baking the generating terminal's width into an archived report makes every rule wrap the moment it is opened somewhere narrower. `COLUMNS=110 filegrail ./case > report.txt` overrides it.

### Commands

| Command | What it does |
| :--- | :--- |
| `filegrail PATH` | Scan a file or directory |
| `filegrail explain FILE` | Show every source behind the findings for one file |
| `filegrail compare A B` | Compare metadata, provenance and timing |
| `filegrail doctor` | Show which local evidence sources are available |
| `filegrail clean PATH --out DIR` | Write copies with the metadata removed |
| `filegrail clean PATH --check` | Say what cleaning would remove, and write nothing |
| `filegrail menu` | Open the interactive menu |
| `filegrail help COMMAND` | Show help for one command |

### Scan options

| Option | Purpose |
| :--- | :--- |
| `-v`, `--verbose` | Every evidence record, not the strongest of each kind |
| `--brief` | Stop at the index: one line a file, no per-file detail |
| `--timeline` | One chronological line per event |
| `--identify` | Extract investigation pivots from metadata |
| `--content` | Also read what the documents say, not only what they record (implies `--identify`) |
| `--cluster` | Group files by the sources more than one of them names |
| `--unknown-only` | Only files nothing was found for |
| `--hash` | Compute SHA-256 for each file |
| `-j`, `--json` | Machine-readable output |
| `--redact` | Redact credentials before printing (also on `explain` and `compare`) |
| `--type NAME` | One family: `archive`, `audio`, `document`, `image`, `mail`, `text`, `video` |
| `--ext LIST` | Only these extensions, e.g. `--ext jpg,pdf` |
| `--limit N` | Cap how many files with no findings the index lists; `0` for all |
| `--home DIR` | Read local evidence from another user profile |
| `--no-recurse` | Do not descend into subdirectories |
| `--no-skip` | Read the directories a scan normally leaves alone |
| `--no-shell-history` | Skip shell-history correlation |
| `--no-archives` | Do not read archives or inherit their origins |
| `--no-color` | Disable ANSI colour |

### Clean options

| Option | Purpose |
| :--- | :--- |
| `--out DIR` | Where the copies go. Required unless `--check`, and never inside the source |
| `--check` | Write nothing; say what would be removed and what would survive |
| `--overwrite` | Replace a file already at the destination path |
| `--type NAME`, `--ext LIST` | The same filters a scan takes |
| `--no-recurse` | Do not descend into subdirectories |

```bash
filegrail help scan
filegrail help clean
```

gives the complete reference.

---

## Practical examples

### One file

```bash
filegrail holiday.jpg
```

```text
  FILES IN DETAIL                                                 1 file
  ──────────────────────────────────────────────────────────────────────

  ● holiday.jpg                                                   3.4 MB

  ACQUISITION  how the file reached this machine
  ← https://portal.example.org/press/2026/holiday-master.jpg
  │ browser download · chromium · 2026-08-31T10:49:33Z      ▰▰▰▰▱ direct
  │ referrer  https://portal.example.org/press/

  INTRINSIC  what the file records about its own earlier life
  ← made by NIKON COOLPIX P6000
  │ device metadata · 2008-10-22T16:28:39Z           ▰▰▰▱▱ self-reported
  │ geo       43.467447, 11.885128
  │
  ├ Make              NIKON
  ├ Model             COOLPIX P6000
  ├ DateTimeOriginal  2008:10:22 16:28:39
  ├ BodySerialNumber  3001234
  ├ GPSLatitudeRef    N
  ├ GPSLatitude       43, 28, 2.81
  ├ GPSLongitudeRef   E
  └ GPSLongitude      11, 53, 6.46
```

The meter on the right is the class of the claim, not a probability: how directly the source knows what it says.

The browser record says **how the bytes reached the machine**. The EXIF block describes **the image before that**. Both stay.

### A directory

```bash
filegrail ./case-files
```

Scans recursively and leads with an overview.

### The whole report, top to bottom

A report is read downwards, and every part of it answers a different question:

| | Section | Answers |
| :--- | :--- | :--- |
| 1 | banner | what was scanned, **whose profile** it was read from, how much of it answered |
| 2 | `INVENTORY` | what the directory is made of — extensions with counts and bytes, then families |
| 3 | `FINDINGS` | what kinds of thing were found, and in how many files |
| 4 | `NOTABLE FINDINGS` | the handful a long report would otherwise bury |
| 5 | `FILES` | **one line per file** — the index. Which of these do I open? |
| 6 | `FILES IN DETAIL` | each of them in full, acquisition then intrinsic then interaction |
| 7 | `METADATA SOURCES` | which readers actually returned something |

Everything before `FILES` fits on one screen. `--brief` stops at `FILES`.

<details>
<summary><strong>▶ Open the whole report, exactly as filegrail prints it</strong></summary>

```text
    __ _ _                   _ _
   / _(_) |___ __ _ _ _ __ _(_) |
  |  _| | / -_) _` | '_/ _` | | |   filegrail 0.5.0
  |_| |_|_\___\__, |_| \__,_|_|_|
              |___/

  Trace where files came from. Extract what they reveal.

  target    ~/Cases/acme
  profile   /mnt/image/home/ann · another machine
  scanned   4 files · 4 types · 3.4 MB
  findings  3 files · 1 without findings

  ──────────────────────────────────────────────────────────────────────

  INVENTORY                                                      4 types
  ──────────────────────────────────────────────────────────────────────

    type files    size    type files    size    type files    size
    JPEG     1  3.4 MB    DOCX     1   498 B    PNG      1    88 B
    MD       1    81 B

    by family
    image     2    document  1    text      1

  FINDINGS
  ──────────────────────────────────────────────────────────────────────

    metadata              3 files
    acquisition evidence  2 files
    authors / creators    1 file
    creating software     2 files
    device information    1 file
    coordinates           1 file
    timestamps            1 file

  NOTABLE FINDINGS
  ──────────────────────────────────────────────────────────────────────

    1 file contains coordinates
    6 unique identifiers extracted (--identify to list them)

  FILES                                                          4 files
  ──────────────────────────────────────────────────────────────────────

  ● chart.png               88 B                        png-text
  ● invoice.docx           498 B  XDG attribute         ooxml-properties
  ● press/holiday.jpg     3.4 MB  browser download      exif
  · notes.md                81 B  2026-09-05T19:37:58Z

  FILES IN DETAIL                                                3 files
  ──────────────────────────────────────────────────────────────────────

  ● invoice.docx                                                   498 B

  ACQUISITION  how the file reached this machine
  ← https://acme-legal.example/portal/invoice.docx
  │ XDG attribute · 2026-09-05T19:37:58Z                    ▰▰▰▰▱ direct

  INTRINSIC  what the file records about its own earlier life
  ← self-reported metadata
  │ OOXML properties                                 ▰▰▱▱▱ self-reported
  │ note      author Ann Shaw
  │
  └ creator  Ann Shaw

  ● press/holiday.jpg                                             3.4 MB

  ACQUISITION  how the file reached this machine
  ← https://portal.example.org/press/2026/holiday-master.jpg
  │ browser download · chromium · 2026-08-31T10:49:33Z      ▰▰▰▰▱ direct
  │ referrer  https://portal.example.org/press/

  INTRINSIC  what the file records about its own earlier life
  ← made by NIKON COOLPIX P6000
  │ device metadata · 2008-10-22T16:28:39Z           ▰▰▰▱▱ self-reported
  │ geo       43.467447, 11.885128
  │
  ├ Make              NIKON
  ├ Model             COOLPIX P6000
  ├ DateTimeOriginal  2008:10:22 16:28:39
  ├ BodySerialNumber  3001234
  ├ GPSLatitudeRef    N
  ├ GPSLatitude       43, 28, 2.81
  ├ GPSLongitudeRef   E
  └ GPSLongitude      11, 53, 6.46

  ● chart.png                                                       88 B
  ← made by GIMP 2.10
  │ PNG text                                         ▰▰▱▱▱ self-reported
  │
  └ Software  GIMP 2.10

  METADATA SOURCES                                             3 sources
  ──────────────────────────────────────────────────────────────────────

    PNG text          ▰▰▱▱▱  1
    XDG attribute     ▰▰▰▰▱  1
    browser download  ▰▰▰▰▱  1

  ──────────────────────────────────────────────────────────────────────
    4 files analyzed · 3 with findings · 1 with no findings
```

</details>

### Triage a large directory

```bash
filegrail ./case-files --brief
```

`--brief` stops at the index. Everything above it — the inventory, the findings, what needs a second look — and then one line per file, with nothing written out in full:

```text
  FILES                                                          4 files
  ──────────────────────────────────────────────────────────────────────

  ● chart.png               88 B                        png-text
  ● invoice.docx           498 B  XDG attribute         ooxml-properties
  ● press/holiday.jpg     3.4 MB  browser download      exif
  · notes.md                81 B  2026-09-05T19:37:58Z
```

A file nothing was found for carries its filesystem date instead of the columns it has nothing to put in them, and `--limit` caps how many of those are listed.

### Files nothing explains

```bash
filegrail ./case-files --unknown-only
```

`no findings` means exactly that: no acquisition record, no metadata, and nothing on this machine that touched the file. It does not mean the file appeared from nowhere.

### Pivots, clusters and timelines

```bash
filegrail ./case-files --identify
filegrail ./case-files --identify --content
filegrail ./case-files --cluster
filegrail ./case-files --timeline
```

With `--content`, each value says which side of the file it came from, and a value on both sides that also appears in how the file arrived is raised where a long report cannot bury it:

```text
  IDENTIFIERS                                                  11 values
  ──────────────────────────────────────────────────────────────────────

    domain  acme-legal.example                          both      2 in 1
            invoice.docx · url
    domain  portal.example.org                          recorded  2 in 1
            holiday.jpg · url
    domain  innafirma.example                           text      1 in 1
            notes.md · line 1
    email   ann.shaw@acme-legal.example                 text      1 in 1
            invoice.docx · body
    email   kontakt@innafirma.example                   text      1 in 1
            notes.md · line 1
    geo     43.46745,11.88513                           recorded  1 in 1
```

### Explain one result

```bash
filegrail explain statement.pdf
```

Use it when the summary is not enough and you want every source, including the ones that disagree. **The answer comes first** — the command exists to be asked *why does filegrail say this*, and an answer printed under everything it rests on is one the reader has to go looking for:

```text
  CONCLUSION

    One record explains how the file arrived, and nothing corroborates
    it. That is the ordinary case, not a weakness, but it rests on
    browser download.

    The file describes an earlier life of its own - NIKON COOLPIX
    P6000 - which says nothing about how it arrived and does not
    contest the record above.

  EVIDENCE STATE

    acquisition  1 record · single source
    intrinsic    1 record
    interaction  none

  ──────────────────────────────────────────────────────────────────────

  ACQUISITION  how the file reached that machine

  ← browser download                                        ▰▰▰▰▱ direct
  │ url       https://portal.example.org/press/2026/holiday-master.jpg
  │ referrer  https://portal.example.org/press/
  │ tool      chromium
  │ at        2026-08-31T10:49:33Z

  ──────────────────────────────────────────────────────────────────────

  INTRINSIC  what the file records about its own earlier life

  ← device metadata                                  ▰▰▰▱▱ self-reported
  │ tool  NIKON COOLPIX P6000
  │ at    2008-10-22T16:28:39Z
  │ geo   43.467447, 11.885128

  ──────────────────────────────────────────────────────────────────────

  RECONCILIATION  single source

    nothing to reconcile
```

Between the conclusion and the material is where the evidence stands, one line per class **whether or not the file has any**. An absent class is a fact about the file, not a gap in the report: a photograph nothing recorded the arrival of is a different thing from one whose arrival record disagrees with itself, and a section that simply does not appear cannot tell those apart.

### Compare two files

```bash
filegrail compare original.jpg edited.jpg
```

Exposes shared device metadata, creation context and timing, and differences in how each file arrived.

### Strip metadata before publishing

```bash
filegrail clean ./photos --out ./cleaned --type image
```

Writes copies without their metadata and leaves the originals alone. `--out` is required unless `--check` is given, and must be outside the directory being read.

The copies mirror the source tree, so two folders each holding a `photo.jpg` produce two copies and not one. A name already taken in the destination is reported and skipped rather than replaced; `--overwrite` says to replace it.

```text
  ● holiday.jpg                                              exif, xmp
  ● chart.png                                                 png-text

    2 files · 2 cleaned · 0 left alone
```

Anything the readers can still see in a copy is listed under `still readable in the copies` — do not publish those.

`--check` runs all of that except the writing, and answers with an exit code:

```bash
filegrail clean ./ready-to-publish --check
```

```text
  nothing written

  ● chart.png                                                   png-text
  ● invoice.docx                                     document properties
  ● notes.md                                 no stripper for this format
  ● press/holiday.jpg                                               exif

  ──────────────────────────────────────────────────────────────────────
    4 files · 3 would be cleaned · 1 left alone
```

`0` means every copy would come out clean, `1` means at least one would not. `--out` is optional under it; given one, the check still reports a name already taken there. Whether or not `--check` was used, the same exit code says whether the copies that were made carry anything a reader can still see.

### Another profile, JSON, redaction

```bash
filegrail /mnt/case/files --home /mnt/case/Users/Alice
filegrail /mnt/evidence --hash --json > filegrail.json
filegrail . --redact --json > report.json
```

---

## How filegrail reasons about evidence

Every result is a claim from one source. A browser database, an EXIF block, a shell command, an XMP packet, a torrent and a recent-document record do not prove the same thing and are not presented as though they do.

| Class | Question | Examples |
| :--- | :--- | :--- |
| **Acquisition** | How did the file reach this machine? | Browser downloads, OS origin metadata, archives, torrents, download sidecars, fetch commands |
| **Intrinsic** | What does the file reveal about its earlier life? | EXIF, XMP, IPTC, C2PA, document and media metadata, archive contents |
| **Interaction** | What touched it after arrival? | Recent documents, shortcuts, sync folders, trash records, non-fetch shell commands |

Agreement between independent sources is reported as corroboration. Disagreement is reported as a conflict rather than resolved silently.

> [!NOTE]
> **A conflict is evidence too.** filegrail shows the disagreement and the sources behind it instead of quietly printing the higher-scoring one.

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

That table is what filegrail decodes **metadata** out of. What it reads as **text** under `--content` is a different axis and a different list — plain text and data files, markup, the zip-based document formats and message bodies, 43 extensions in all.

The readers define what is supported, not either table. The complete matrix for both is in [`docs/FORMATS.md`](docs/FORMATS.md), which is held against the code by a test and so cannot drift.

A format filegrail does not understand is reported as not understood — and still takes part in provenance analysis when local evidence about it exists.

---

## JSON and automation

`--json` is available on every command — `filegrail.scan/1`, `filegrail.explain/1`, `filegrail.compare/1`, `filegrail.doctor/1` and `filegrail.clean/1` — and each document names its schema and the version that produced it:

```json
{
  "schema": "filegrail.scan/1",
  "filegrail_version": "0.5.1",
  "root": "/mnt/evidence"
}
```

It preserves file records, acquisition/intrinsic/interaction claims, decoded metadata, sources, confidence values, findings and conflicts, identifiers, shared-source clusters and file relationships.

---

## Privacy and safety

filegrail runs locally, makes **no network requests** and does not modify what it inspects.

Its output is another matter: local evidence can carry private URLs, credentials, tokens, paths and addresses.

```bash
filegrail . --redact --json > report.json
```

`--redact` removes credentials from URLs, commands and free-text fields while keeping enough structure for repeated values to stay recognisable.

It is available on `scan`, `explain` and `compare` — every command that renders evidence. `explain` is the one that prints the most of it, since its job is to show every source behind a finding including the ones that disagree.

```bash
filegrail explain statement.pdf --redact
```

> [!WARNING]
> Redaction is biased towards precision, not towards catching everything. Always review investigation output before sharing it.

---

## Limits

filegrail can only analyze evidence that still exists. Browser history gets cleared, extended attributes are lost in copies, shell history may carry no timestamps, and some files never had metadata.

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
mypy
```

`mypy` runs in strict mode over `src/filegrail`, against the oldest supported interpreter.

The two hand-written binary decoders — CBOR, which a C2PA manifest is written in, and bencode, which a `.torrent` is — also have property tests, driven by `hypothesis`. They live in a separate extra and their own CI job, because they are the one thing here whose result depends on a seed rather than on the code:

```bash
python -m pip install -e ".[dev,fuzz]"
pytest tests/test_properties.py
```

Without that extra they skip; `tests/test_malformed.py`, which cuts a file of every supported format short and hands the pieces to every reader, needs nothing and runs with the rest.

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before adding a reader or changing what a source is taken to prove. [`SECURITY.md`](SECURITY.md) covers what to report privately, and [`CHANGELOG.md`](CHANGELOG.md) carries the history.

---

## License

Apache License 2.0. See [`LICENSE`](LICENSE).

---

<div align="center">

**filegrail**

*Reconstruct how files arrived. Extract what they reveal.*

Made by [osint-shifu](https://github.com/osint-shifu)

</div>
