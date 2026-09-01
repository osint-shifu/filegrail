<a id="top"></a>

<div align="center">
  <img src="assets/filetrail-banner.svg" alt="filetrail - trace origins, extract metadata" width="820">
  <p><strong>Trace origins, extract metadata.</strong></p>
  <p>
    Fast, local file provenance and metadata analysis from traces your machine
    and the files themselves already contain.
  </p>
  <p>
    <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square">
    <img alt="68 file extensions" src="https://img.shields.io/badge/formats-68-8250df?style=flat-square">
    <img alt="Zero runtime dependencies" src="https://img.shields.io/badge/runtime_dependencies-0-1f883d?style=flat-square">
    <img alt="Local and read-only" src="https://img.shields.io/badge/local_%26_read--only-yes-1f883d?style=flat-square">
    <img alt="Network requests" src="https://img.shields.io/badge/network_requests-none-1f883d?style=flat-square">
    <img alt="License: Apache 2.0" src="https://img.shields.io/badge/license-Apache--2.0-8250df?style=flat-square">
    <a href="https://github.com/osint-shifu/filetrail/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/osint-shifu/filetrail/actions/workflows/ci.yml/badge.svg"></a>
  </p>
  <p>
    <a href="#what-filetrail-does">What it does</a> ·
    <a href="#installation">Installation</a> ·
    <a href="#quick-start">Quick start</a> ·
    <a href="#metadata-analysis">Metadata</a> ·
    <a href="#provenance-and-evidence">Evidence</a> ·
    <a href="#investigation-workflows">Workflows</a> ·
    <a href="FORMATS.md">Formats</a>
  </p>
</div>

---

## What filetrail does

You have a folder full of files - a case directory, a download folder, an unpacked archive. You want to know **where they came from, what they reveal, and what happened to them**. All of them, in one pass.

`filetrail` combines two things that are usually analyzed separately:

* **metadata extraction and file analysis**
* **retroactive provenance reconstruction**

It extracts metadata from **68 file extensions**, including EXIF, XMP, IPTC, C2PA, PDF, Office, OpenDocument, EPUB, MP4, Matroska, FLAC, WAV and email formats.

At the same time, it checks traces already left on the machine:

* browser download history
* Windows origin metadata
* macOS where-from and quarantine records
* Linux XDG attributes
* archive membership
* shell history
* recent-document records

Then it correlates the results while keeping three questions separate:

1. **How did the file reach this machine?**
2. **What does the file say about its earlier life?**
3. **What touched it after arrival?**

> [!IMPORTANT]
> `filetrail` works after the fact. No agent, monitoring service, provenance database or prior setup needs to exist before the file appears.

### Fast by design

`filetrail` is intentionally small and direct:

* no daemon
* no index to build
* no provenance database
* no network requests
* no runtime dependencies
* no writes to inspected files

It reads what is already there and reports what the available evidence actually supports.

---

## Installation

Requires **Python 3.10+**.

```bash
pipx install git+https://github.com/osint-shifu/filetrail
```

Or run it directly from a checkout:

```bash
PYTHONPATH=src python -m filetrail.cli /path/to/files
```

Runtime dependencies: **zero**.

---

## Quick start

Inspect a file or directory:

```bash
filetrail /path/to/files
```

Common workflows:

```bash
filetrail suspicious.pdf
filetrail . --unknown-only
filetrail explain statement.pdf
filetrail compare a.jpg b.jpg
filetrail . --identify
filetrail . --timeline
filetrail doctor
filetrail menu
```

Useful options:

```bash
filetrail . --verbose
filetrail . --brief
filetrail . --json
filetrail . --hash
filetrail . --redact
filetrail . --type image
filetrail . --ext jpg,pdf
filetrail . --no-recurse
filetrail . --no-shell-history
filetrail . --no-archives
filetrail . --no-color
```

Run `filetrail doctor` when missing evidence matters. It shows which local sources are available and, where possible, how far back they reach.

---

## Metadata analysis

Metadata is not an add-on in `filetrail`. It is one of the core evidence layers.

The tool extracts and normalizes useful metadata from files while preserving the fields that may matter during an investigation.

Examples include:

* camera make, model and serial number
* capture and creation timestamps
* GPS coordinates
* authors, editors and organizations
* creating and editing applications
* document properties
* XMP derivation relationships
* XMP editing history
* IPTC bylines, credits, locations and captions
* C2PA Content Credentials
* audio and video encoder information
* PDF metadata
* Office and OpenDocument properties
* email headers and delivery hops
* archive member information

Normal output keeps decoded fields visible as a tree. Use `--brief` for a more compact view or `--json` when feeding results into other tooling.

### Investigation pivots

`--identify` extracts useful values from decoded metadata while preserving the file and field they came from.

```bash
filetrail ./case-files --identify
```

Supported pivot classes include:

* URLs
* domains
* email addresses
* IP addresses
* hashes
* coordinates

A camera serial, domain, author name, GPS position or embedded URL can be more valuable than the file name itself.

For the complete format and metadata matrix, see [`FORMATS.md`](FORMATS.md).

---

## Provenance and evidence

`filetrail` does not collapse everything into one "origin" field.

```text
file
├── acquisition    how it reached this machine
├── intrinsic      what the file says about its earlier life
└── interaction    what touched it after arrival
```

Think of the result as an **evidence map**, not a metadata dump.

A single image can contain all of these at once:

* a browser URL showing how it was downloaded
* EXIF identifying the camera
* GPS coordinates from capture time
* XMP or C2PA describing later processing
* recent-document records showing which application opened it

Those are different claims from different sources. `filetrail` keeps them separate.

### Evidence classes

| Class | Question | Typical sources |
| :--- | :--- | :--- |
| **Acquisition** | How did the file reach this machine? | Browser history, OS origin metadata, archive inheritance, fetch commands |
| **Intrinsic** | What does the file reveal about its earlier life? | EXIF, XMP, IPTC, C2PA, document and media metadata |
| **Interaction** | What touched it after arrival? | Recent documents, Windows shortcuts, shell commands |

Confidence values help rank **competing claims of the same type**. They are not probability scores and not forensic verdicts.

### When sources disagree

Conflicts are reported rather than silently resolved.

`filetrail` can detect or surface:

* conflicting acquisition URLs
* matching evidence from independent sources
* filename-only matches
* size mismatches
* timeline inconsistencies
* disagreements between metadata blocks
* derivation relationships between related files

> [!NOTE]
> A conflict is evidence too. `filetrail` shows the disagreement and the sources behind it instead of inventing certainty.

---

## Investigation workflows

### Inspect one file

```bash
filetrail holiday.jpg
```

Example:

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
├ Software           Nikon Transfer 1.1 W
└ DateTimeOriginal   2008:10:22 16:28:39
```

The browser record explains how the bytes reached the machine. The file metadata tells you about the image before that.

Both remain visible.

### Explain the evidence

```bash
filetrail explain statement.pdf
```

Use `explain` when you want to see every source supporting or contradicting a result.

### Compare two files

```bash
filetrail compare a.jpg b.jpg
```

Comparison can expose shared device metadata, creation context, timing and differences in acquisition history.

### Find files nothing was found for

```bash
filetrail ./case-files --unknown-only
```

`no findings` means exactly that: **no acquisition record, no metadata, and nothing on this machine that touched the file**.

It does not mean the file appeared from nowhere.

### Build a timeline

```bash
filetrail ./case-files --timeline
```

Acquisition, creation and recorded editing events can be viewed chronologically instead of as isolated metadata fields.

---

## Supported formats

Readers currently cover **68 file extensions** across major file families.

| Family | Examples |
| :--- | :--- |
| Images | JPEG, TIFF, DNG, NEF, CR2, ARW, WebP, HEIC, AVIF, PNG, APNG |
| Documents | PDF, DOCX, XLSX, PPTX, DOC, XLS, PPT |
| OpenDocument | ODT, ODS, ODP, ODG, OTT, OTP |
| Video / audio | MP4, MOV, M4A, MP3, WAV, AVI, MKV, WebM, FLAC, OGG, Opus |
| Books / markup | EPUB, RTF, SVG |
| Notebooks | IPYNB |
| Email | EML, MSG |
| Archives | ZIP, TAR and compressed TAR variants |

Metadata layers include **EXIF, XMP, IPTC IIM and C2PA** where supported by the container.

Files in unsupported formats are still scanned for available provenance evidence.

See [`FORMATS.md`](FORMATS.md) for the complete matrix.

---

## Command reference

| Command | What it does |
| :--- | :--- |
| `filetrail PATH` | Scan a file or directory |
| `filetrail explain FILE` | Show the evidence behind a result |
| `filetrail compare FILE_A FILE_B` | Compare metadata, provenance and timing |
| `filetrail doctor` | Inspect available evidence sources |
| `filetrail menu` | Open the interactive terminal interface |

Useful scan options include:

`--verbose`, `--brief`, `--json`, `--hash`, `--redact`, `--identify`, `--timeline`, `--unknown-only`, `--type`, `--ext`, `--limit`, `--home`, `--no-recurse`, `--no-shell-history`, `--no-archives`, `--no-color`.

---

## Analyze another user profile

By default, `filetrail` reads evidence from the current user's home directory.

`--home` points the same readers at another mounted or copied profile:

```bash
filetrail /mnt/case/files --home /mnt/case/Users/Alice
filetrail doctor --home /mnt/case/Users/Alice
```

This is useful when working with evidence copied from another system.

Browser profiles can be analyzed across platforms. For example, a Windows Chromium profile can be examined while running `filetrail` on Linux.

`--home` is not a disk-image parser. It expects an accessible user profile and reads the same sources it would inspect locally.

---

## Terminal output

The default interface is a dense terminal report rather than a dashboard.

Colour indicates **how `filetrail` knows something**, not whether the result is good, bad or suspicious.

Output supports:

* colour terminals
* plain text
* `NO_COLOR`
* `--no-color`
* ASCII fallback
* JSON

The terminal and evidence design are documented in [`DESIGN.md`](DESIGN.md).

---

## JSON and automation

Need structured data instead of terminal output?

```bash
filetrail /mnt/evidence --hash --json > filetrail.json
```

JSON preserves:

* file records
* provenance claims
* decoded metadata
* evidence sources
* confidence values

This makes the output suitable for scripts, investigation tooling and larger analysis pipelines.

The main command families expose versioned schemas such as:

```json
{
  "schema": "filetrail.scan/1",
  "filetrail_version": "0.1.0",
  "root": "/mnt/evidence"
}
```

---

## Privacy

Everything runs locally.

`filetrail` makes **no network requests**.

That does not automatically make reports safe to publish. Local evidence can contain credentials, tokens, private URLs or other sensitive information.

Use:

```bash
filetrail . --redact --json > report.json
```

`--redact` hides credentials in URLs, referrers, commands and decoded free-text fields while preserving enough structure for repeated values to remain recognizable.

> [!WARNING]
> Always review investigation output before sharing it.

---

## Limits

`filetrail` can only analyze evidence that still exists.

Browser history can be cleared. Extended attributes disappear during copies. Shell history may lack timestamps. Some files never carried origin metadata.

`filetrail` is deliberately:

* **not proof**
* **not chain of custody**
* **not a full disk-image forensic suite**
* **not a monitoring agent**
* **not a background collector**

It reconstructs what it can from surviving local evidence and file metadata.

C2PA manifests are parsed, but their cryptographic signatures are currently **not verified**.

Three readers are written from the specification and have never been run against a file the originating software produced: Outlook `.msg` messages, Windows `.lnk` shortcuts, and the `id3 ` chunk a WAV file may carry. [`FORMATS.md`](FORMATS.md) names them and says why.

Use `filetrail doctor` to understand what evidence sources are actually available before drawing conclusions from missing data.

---

## Status

**Working alpha.**

Current version: **0.1.0**.

The core remains intentionally small:

* Python 3.10+
* standard library only
* zero runtime dependencies
* no service to run
* no dependency tree to maintain

See [`CHANGELOG.md`](CHANGELOG.md) for project history.

---

## Contributing

The most useful contributions are:

* new evidence sources
* new metadata readers
* additional real-world test files
* improvements to format coverage

Messaging apps, download managers, sync clients, package managers and other local tools often leave traces that can help reconstruct where a file came from.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
ruff check .
```

---

## Security

Found something that could expose investigation data, bypass `--redact`, leak credentials or allow a crafted file to access data outside the scan target?

Please do not open a public issue.

Follow [`SECURITY.md`](SECURITY.md).

---

## License

Apache License 2.0.

See [`LICENSE`](LICENSE).

---

<div align="center">
  <strong>Trace origins, extract metadata.</strong>
</div>
