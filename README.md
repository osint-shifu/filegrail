<a id="top"></a>

<div align="center">
  <img src="assets/filetrail-banner.svg" alt="filetrail — trace where files came from" width="820">
  <p>Retroactive file provenance from traces your machine already has.</p>
  <p>
    <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square">
    <img alt="Zero runtime dependencies" src="https://img.shields.io/badge/runtime_dependencies-0-1f883d?style=flat-square">
    <img alt="Local and read-only" src="https://img.shields.io/badge/local_%26_read--only-yes-1f883d?style=flat-square">
    <img alt="Network requests" src="https://img.shields.io/badge/network_requests-none-1f883d?style=flat-square">
    <img alt="License: Apache 2.0" src="https://img.shields.io/badge/license-Apache--2.0-8250df?style=flat-square">
    <a href="https://github.com/osint-shifu/filetrail/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/osint-shifu/filetrail/actions/workflows/ci.yml/badge.svg"></a>
  </p>
  <p><strong><a href="#about-filetrail">About</a></strong> · <a href="#installation">Installation</a> · <a href="#quick-start">Quick start</a> · <a href="#evidence-model">Evidence</a> · <a href="#supported-metadata">Metadata</a> · <a href="#command-reference">Commands</a> · <a href="CONTRIBUTING.md">Contributing</a></p>
</div>

---

<a id="about-filetrail"></a>

## About filetrail

You have a file. You want to know **where it came from**.

`filetrail` checks the traces already left on the machine: browser history, OS origin metadata, archives, shell history, C2PA Content Credentials, EXIF, document metadata and recent-file records.

Then it puts those pieces into one report and keeps three questions separate:

- **How did the file get here?**
- **What does the file say about where it came from before that?**
- **What touched it after it arrived?**

> [!IMPORTANT]
> `filetrail` works after the fact. No agent, database or monitoring setup needs to exist before the file shows up.

### Why bother?

Because the answer is usually scattered.

The browser may know the URL. The OS may have saved an origin attribute. An archive may explain how an extracted file got here. EXIF may point to a camera and location. C2PA may describe how media was created or edited. Shell history may show a fetch command.

`filetrail` pulls those clues together without pretending they all mean the same thing.

### Fast by design

There is not much standing between the command and the result:

- no daemon;
- no index to build;
- no provenance database;
- no network requests;
- no runtime dependencies;
- no writes to inspected files.

It reads what is already there and reports what it can actually support.

<a id="table-of-contents"></a>

## Table of contents

- [Installation](#installation)
- [Quick start](#quick-start)
- [How it works](#how-it-works)
- [Evidence model](#evidence-model)
- [Investigation workflows](#investigation-workflows)
- [Supported metadata](#supported-metadata)
- [Command reference](#command-reference)
- [Terminal output](#terminal-output)
- [JSON and automation](#json-and-automation)
- [Privacy and safe sharing](#privacy)
- [Limits](#limits)
- [Status](#status)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)

---

<a id="installation"></a>

## Installation

Requires **Python 3.10+**.

```bash
pipx install git+https://github.com/osint-shifu/filetrail
```

Or run it straight from a checkout:

```bash
PYTHONPATH=src python -m filetrail.cli /path/to/files
```

Runtime dependencies: **zero**.

<p align="right"><a href="#table-of-contents">Back to contents ↑</a></p>

---

<a id="quick-start"></a>

## Quick start

```bash
filetrail /path/to/files
```

Useful commands:

```bash
filetrail suspicious.pdf        # inspect one file
filetrail . --unknown-only      # files with no recorded acquisition origin
filetrail explain statement.pdf # show every source behind the result
filetrail compare a.jpg b.jpg   # compare two files and their histories
filetrail . --identify          # pull useful identifiers from metadata
filetrail . --timeline          # chronological view
filetrail doctor                # see what this machine can answer
filetrail menu                  # interactive terminal front end
```

Useful scan options:

```bash
filetrail . --verbose           # show every evidence record
filetrail . --brief             # compact metadata output
filetrail . --json              # machine-readable output
filetrail . --hash              # add SHA-256
filetrail . --redact            # hide credentials before printing
filetrail . --type image        # filter by broad file type
filetrail . --ext jpg,pdf       # filter by extension
filetrail . --limit 100         # limit unexplained-file output; 0 for all
filetrail . --no-recurse        # current directory only
filetrail . --no-shell-history  # skip shell-history correlation
filetrail . --no-archives       # disable archive-origin inheritance
filetrail . --no-color          # plain text output
```

> [!TIP]
> Run `filetrail doctor` when you care about missing evidence. It shows which local sources are available and, where possible, how far back they go.

<p align="right"><a href="#table-of-contents">Back to contents ↑</a></p>

---

<a id="how-it-works"></a>

## How it works

`filetrail` does not squeeze provenance into one field. It keeps different kinds of evidence separate.

```text
file
├── acquisition    how it reached this machine
├── intrinsic      what the file says about its earlier life
└── interaction    what touched it after arrival
```

Think of it as an evidence map, not a metadata dump.

One photo can have all of these at once:

- a browser URL showing how it was acquired;
- EXIF pointing to the camera that created it;
- GPS coordinates from capture time;
- C2PA records describing later processing;
- recent-document records showing which app opened it.

Those are different facts. `filetrail` keeps them that way.

### When sources disagree

If two sources tell different stories, `filetrail` does not quietly pick a winner.

It can flag:

- matching evidence from independent sources;
- conflicting acquisition URLs;
- same-host or same-path mismatches;
- filename-only matches;
- recorded-size mismatches;
- timelines that do not line up;
- a file whose own two accounts of itself disagree. Four pairings are checked,
  each of them published rather than guessed: IPTC IIM against XMP, a camera's
  EXIF tags against their XMP mirror, a PDF's `Info` dictionary against its XMP,
  and a PNG's text chunks against its XMP. An editor maintains one block while
  leaving the other as it found it, so a difference is the trace of an
  attribution being changed - a PDF whose `Info` names InDesign while its XMP
  still names the Illustrator document it was exported from, say. Timestamps are
  compared as moments and exposure settings not at all, because a zone or a
  comma decimal is two tools spelling one fact, not two facts.

It also links the scanned files to each other where XMP says how they were made:
a master, the export derived from it and the rendition derived from that are
reported as a chain, in both directions. A shared *original* document is only
ever reported as a common ancestor - a template carries its XMP block into every
file made from it, and those files share an ancestor and nothing else.

> [!IMPORTANT]
> A conflict is useful evidence too. `filetrail` shows it and lets you decide what it means.

<p align="right"><a href="#table-of-contents">Back to contents ↑</a></p>

---

<a id="evidence-model"></a>

## Evidence model

### Evidence classes

| Class | Question | Typical sources |
|:---|:---|:---|
| **Acquisition** | How did this file reach this machine? | Browser history, `Zone.Identifier`, macOS where-from metadata, macOS quarantine records, Linux XDG attributes, archive inheritance, fetch commands, mail `Received:` hops |
| **Intrinsic** | What does the file say about its earlier life? | EXIF, document metadata, C2PA, camera/device metadata |
| **Interaction** | What touched it after arrival? | Recent documents, Windows Recent shortcuts, non-fetching shell commands |

### Evidence sources

Confidence helps rank **competing claims of the same kind**. It is not a probability score and not a forensic verdict.

| Source | What it can provide | Confidence |
|:---|:---|---:|
| Browser downloads | Source URL, referrer, redirect chain, timestamp, size | 90 |
| Windows `Zone.Identifier` | `HostUrl`, `ReferrerUrl`, zone | 85 |
| macOS `kMDItemWhereFroms` | URL, referrer | 85 |
| Linux XDG xattrs | Origin URL, referrer | 80 |
| Mail delivery | The topmost `Received:` hop: the connecting address and the server that saw it | 78 |
| Archive membership | Inherited origin of extracted members | 70 |
| C2PA Content Credentials | Producing application, creation info, digital source type | 60 |
| Device metadata | Camera/device, capture time, GPS and decoded fields | 55 |
| XMP | Creating application, author, derivation ids and decoded properties | 52 |
| XMP history | One recorded edit: which application, what it did and when | 52 |
| IPTC IIM | Press byline, credit, source, copyright, place and date | 51 |
| Document metadata | Producer, author, creation data and format-specific fields | 50 |
| Mail relay | Any hop below the top, which the sender may have written | 45 |
| Shell history | Fetching or handling command | 40 |
| Recent documents | Application interaction and time | 35 |
| Mail headers | What the message says about itself: sender, subject, composing client | 30 |
| Filesystem | Creation/modification timestamps where available | 10 |

A few details worth knowing:

- Chromium-family browsers and Firefox are read directly from local history databases.
- Browser databases are copied before SQLite is opened, so a running browser is left alone.
- A browser record can still match after a file was moved. Filename-only matches are marked as such.
- Files extracted from ZIP/TAR-family archives can inherit the archive origin when member name and size match.
- Linux origin xattrs are useful when present, but coverage varies a lot.
- C2PA manifests are parsed, but their cryptographic signatures are **not verified**.
- A place and a coordinate are kept apart. `geo` holds a latitude/longitude pair this
  tool decoded itself, from EXIF or an ISO 6709 atom; `location` holds a place written
  as a name, which is what IPTC records and what somebody typed. Only one of the two
  can be put on a map without believing anybody.
- IPTC IIM predates XMP, and modern tools maintain XMP while leaving the IIM block as
  they found it. A byline there is often a record of an earlier state of the file,
  which makes it weaker as a claim and useful as evidence.
- XMP is unsigned free text an application writes about itself. Each recorded edit
  becomes a claim of its own, so an editing sequence lands on `--timeline` beside the
  download that brought the file in. An edit with no recorded time stays a field
  rather than becoming a dated event.
- Shell history and recent-document records are intentionally treated as weaker evidence. They can show contact without proving acquisition.

<p align="right"><a href="#table-of-contents">Back to contents ↑</a></p>

---

<a id="investigation-workflows"></a>

## Investigation workflows

### Inspect one file

```bash
filetrail holiday.jpg
```

A report can keep acquisition and file metadata side by side:

```text
  ● holiday.jpg                                                         3.4 MB
  ← https://portal.example.org/press/holiday.jpg
  │ browser download · firefox · 2026-08-24T19:02:11Z             ▰▰▰▰▱ direct
  │
  ← made by NIKON COOLPIX P6000
  │ device metadata · 2008-10-22T16:28:39Z                 ▰▰▰▱▱ self-reported
  │ geo       43.467448, 11.885127
  │
  ├ Make               NIKON
  ├ Model              COOLPIX P6000
  ├ BodySerialNumber   3001234
  ├ Software           Nikon Transfer 1.1 W
  ├ DateTimeOriginal   2008:10:22 16:28:39
  ├ GPSDateStamp       2008:10:23
  └ GPSTimeStamp       14, 36, 47.23
```

The browser record explains how the bytes got onto the machine. EXIF tells you something about the image before that. Both stay visible.

### Explain a conflict

```bash
filetrail explain statement.pdf
```

```text
  acquisition  how the file reached this machine

    browser download    https://example.com/statement.pdf               direct
    Windows zone        https://mirror.example.net/statement.pdf        direct

  reconciliation  conflict

    source_conflict     browser download says
                        https://example.com/statement.pdf
    source_conflict     Windows zone says
                        https://mirror.example.net/statement.pdf
```

No fake certainty. You get the disagreement and the sources behind it.

### Compare two files

```bash
filetrail compare a.jpg b.jpg
```

```text
  identical

    Make              Canon
    Model             EOS R5
    BodySerialNumber  042117000123
    Software          Canon EOS R5

  arrived by

    a.jpg             browser download: https://forum.example.org/t/1/a.jpg
    b.jpg             no acquisition record

  created

    apart             14 seconds
```

Shared metadata can link two files to the same device or creation context even when they arrived in different ways.

### Find files with no recorded origin

```bash
filetrail ./case-files --unknown-only
```

`no recorded origin` means exactly that: **no surviving acquisition record was found**.

It does not mean the file appeared from nowhere.

Use `filetrail doctor` alongside it to see what evidence sources are still available on the machine.

### Pull investigation pivots

```bash
filetrail ./case-files --identify
```

`--identify` extracts useful values from decoded metadata and keeps the file and field they came from.

Supported classes include URLs, domains, email addresses, IP addresses, hashes and coordinates.

<p align="right"><a href="#table-of-contents">Back to contents ↑</a></p>

---

<a id="supported-metadata"></a>

## Supported metadata

`filetrail` keeps the fields its readers can actually decode. Normal output shows them as a tree, `--brief` folds them down, and `--json` keeps them for scripts and other tooling.

The table below is the summary. [`FORMATS.md`](FORMATS.md) has the complete list — every extension, the metadata block each one produces, what is deliberately not read, and which readers are written from a specification rather than tested against real files. It is checked against the code by a test, so it cannot go stale.

| Family | Formats | Examples of data read |
|:---|:---|:---|
| Images | JPEG, TIFF, DNG, NEF, CR2, ARW, WebP, HEIC, AVIF | EXIF camera/device data, software, capture time, artist, GPS |
| PNG | PNG, APNG | Text chunks, software, creation time, author, recorded generation parameters |
| Content Credentials | PNG, JPEG | C2PA/JUMBF producing application, creation data, digital source type |
| XMP | JPEG, TIFF and raw, PNG, PDF, MP4, HEIC, SVG and any other container that embeds a packet | Creating application, author, title, derivation ids, and every recorded editing step |
| IPTC IIM | JPEG, TIFF, PSD - any Photoshop image-resource block, plus TIFF tag 33723 | By-line, credit, source, copyright, headline, caption, keywords, place and date of creation |
| Video / audio | MP4, M4V, MOV, 3GP, M4A, MP3, WAV, AVI, MKV, WebM, MKA, FLAC, OGG, Opus | Encoder, device, creation time, ISO 6709 location, ID3 frames, RIFF `INFO` fields, BWF `bext` recorder and coding history, Matroska writing application, segment date and tags, Vorbis comments |
| PDF | PDF | `Info` dictionary, including compressed object streams and hex strings |
| Office Open XML | DOCX, XLSX, PPTX and macro/template variants | Application, author, last editor, company, creation data and document properties |
| Legacy Office | DOC, XLS, PPT and template variants | SummaryInformation / DocumentSummaryInformation properties |
| OpenDocument | ODT, ODS, ODP, ODG, OTT, OTP | Generator, author, creation and editing metadata |
| Books / markup | EPUB, RTF, SVG | Package metadata, generator information |
| Notebooks | IPYNB | Kernel and language runtime |
| Mail | EML, MSG | Every `Received:` hop as its own event, the connecting address each server saw, and the sender's own headers kept apart from them. A `.msg` keeps the same header block in a MAPI stream; where an Exchange delivery left none, its own properties are reported and no delivery record is invented |
| Archives | ZIP, TAR and compressed TAR variants | Member names and uncompressed sizes used for origin inheritance |

Other files are still scanned. If `filetrail` does not understand metadata in a format, it says so instead of making something up.

### Why keep all those fields?

Because you rarely know in advance which one will matter.

A camera serial can tie images to one device. GPS time can be more useful than the camera clock. Office metadata can expose the last editor, company, template, revision count or editing duration.

So decoded fields stay visible by default. Long values wrap instead of being chopped off.

Vendor-specific camera maker notes are the main exception. They need manufacturer-specific parsers and are not decoded yet.

<p align="right"><a href="#table-of-contents">Back to contents ↑</a></p>

---

<a id="command-reference"></a>

## Command reference

| Command | What it does |
|:---|:---|
| `filetrail PATH` | Scan a file or directory and reconstruct available provenance |
| `filetrail explain FILE` | Show every evidence source behind the result |
| `filetrail compare FILE_A FILE_B` | Compare metadata, provenance and timing |
| `filetrail doctor` | Show which evidence sources are available, and how far back they reach |
| `filetrail menu` | Open the interactive terminal front end |

Useful options: `--verbose`, `--brief`, `--json`, `--hash`, `--redact`, `--identify`, `--timeline`, `--unknown-only`, `--type`, `--ext`, `--limit`, `--home`, `--no-recurse`, `--no-shell-history`, `--no-archives`, `--no-color`.

### Reading a machine that is not this one

By default every source is read from the current user's home directory, which answers *what does my machine remember about my files*. `--home` points the same readers at another profile, which answers *here is a mounted image, reconstruct what its machine remembered*.

```bash
filetrail /mnt/case/files --home /mnt/case/Users/Alice
filetrail doctor --home /mnt/case/Users/Alice
```

It works across platforms: a Windows Chrome profile can be read from Linux, because the profile locations for all three systems are searched under whatever `--home` is given. `scan`, `explain`, `compare` and `doctor` all take it.

Two things change when it is used. Download records keep the path the other machine wrote, so they usually match on file name and size rather than on path - the report says which. And the report stops saying `this machine`, because it is not; it names the profile it read instead.

A `--home` that does not exist is an error rather than an empty result. A run that found nothing because it looked in the wrong place should not look like a run that found nothing because there was nothing to find.

<p align="right"><a href="#table-of-contents">Back to contents ↑</a></p>

---

<a id="terminal-output"></a>

## Terminal output

The default UI is a dense terminal report, not a dashboard.

Colour tells you **how `filetrail` knows**, not whether something is good, bad or suspicious.

The output still works without styling:

- colour when the terminal supports it;
- plain text when piped, under `NO_COLOR`, or with `--no-color`;
- ASCII fallback when Unicode is unavailable;
- JSON when you want to script it.

The terminal design and evidence colours are documented in [`DESIGN.md`](DESIGN.md).

<p align="right"><a href="#table-of-contents">Back to contents ↑</a></p>

---

<a id="json-and-automation"></a>

## JSON and automation

Need the data, not the pretty terminal output?

```bash
filetrail /mnt/evidence --hash --json > filetrail.json
```

JSON keeps file records, origin claims, decoded fields and confidence values, so you can feed the result into scripts, case tooling or another analysis workflow without scraping terminal text.

Every document begins by saying what it is:

```json
{
  "schema": "filetrail.scan/1",
  "filetrail_version": "0.1.0",
  "root": "/mnt/evidence"
}
```

Four commands emit JSON and each has its own shape: `filetrail.scan/1`,
`filetrail.explain/1`, `filetrail.compare/1`, `filetrail.doctor/1`. Switch on
`schema` rather than guessing from the keys. The number changes only when a
field changes meaning or leaves - a new field is not a break, and neither is a
release, which is why the version sits in its own key beside it.

Each claim carries two names for where it came from. `source` says what the
reader found - `device-metadata` where a file named a camera, `document-metadata`
where it did not - and is what `confidence` ranks. `block` says which metadata
block was decoded: `pdf-info`, `png-text`, `exif`, `ole-summary`, `iptc`, `xmp`.
Nine readers answer to `document-metadata`, so `block` is the field to filter on
when you want the PDFs rather than everything a file said about itself. A record
that decoded no metadata block - a browser download, a shell command - has no
`block` at all.

<p align="right"><a href="#table-of-contents">Back to contents ↑</a></p>

---

<a id="privacy"></a>

## Privacy and safe sharing

Everything runs locally. `filetrail` makes no network requests.

That does not mean the output is automatically safe to share. Local evidence can contain API keys, session tokens, credentials or sensitive URLs.

Before sharing a report:

```bash
filetrail . --redact --json > report.json
```

`--redact` hides credentials in URLs, referrers, commands and decoded free-text fields. Repeated secrets get short non-reversible fingerprints, so you can still see that the same value appeared more than once.

> [!WARNING]
> Redaction helps. Still review the output before publishing it.

<p align="right"><a href="#table-of-contents">Back to contents ↑</a></p>

---

<a id="limits"></a>

## Limits

`filetrail` can only read evidence that still exists.

Browser history gets cleared. Profiles get reset. Extended attributes disappear during copies. Shell history may have no timestamps. Some files never had origin metadata at all.

That is why `filetrail doctor` exists: it tells you what sources are available and, where possible, how far back they reach.

`filetrail` is deliberately:

- **not proof** - local records are evidence and can be changed;
- **not chain of custody** - it reconstructs history, it does not establish custody;
- **not a disk-image forensic suite** - it works on files and directories;
- **not a collector** - it reads existing traces instead of running a monitoring layer.

C2PA manifests are parsed, but signatures are not cryptographically verified.

Three readers are written from the specification and have never been run
against a file the originating software produced, because nothing available
here writes one: Outlook `.msg` messages, Windows `.lnk` shortcuts, and the
`id3 ` chunk a WAV file may carry. The
container walk under the `.msg` reader is not in that position - it is the same
one real `.doc` files exercise.

The macOS quarantine attribute is read under both `com.apple.quarantine` and
`user.com.apple.quarantine`. Only the first exists on macOS itself; the second
is how a copy carries it onto another system, and it is the only one that can be
written outside macOS. The quarantine database is ordinary SQLite and is read
the same way anywhere.

`--home` reads another user profile, which is not the same as reading a disk
image. It expects a mounted or copied home directory, and it reads the same
sources it would read here; nothing about it parses a filesystem.

<p align="right"><a href="#table-of-contents">Back to contents ↑</a></p>

---

<a id="status"></a>

## Status

**Working alpha.** Everything documented here is implemented.

Current version: **0.1.0**.

The core stays intentionally small: Python 3.10+, standard library only, no service to run and no runtime dependency tree to babysit.

See [`CHANGELOG.md`](CHANGELOG.md) for project history.

<p align="right"><a href="#table-of-contents">Back to contents ↑</a></p>

---

<a id="contributing"></a>

## Contributing

The most useful contributions are simple: **more evidence sources** and **more metadata readers**.

Messaging apps, download managers, sync clients, package managers and plenty of other local tools leave traces that can explain where a file came from. New format readers make the same idea useful for more files.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request.

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
ruff check .
```

<p align="right"><a href="#table-of-contents">Back to contents ↑</a></p>

---

<a id="security"></a>

## Security

Found something that could expose investigation data, leak credentials past `--redact`, or let a crafted file read outside the scanned directory?

Please do not open a public issue. Follow [`SECURITY.md`](SECURITY.md).

<p align="right"><a href="#table-of-contents">Back to contents ↑</a></p>

---

<a id="license"></a>

## License

Apache License 2.0. See [`LICENSE`](LICENSE).

---

<div align="center">
  <strong>Trace where files came from.</strong>
</div>
