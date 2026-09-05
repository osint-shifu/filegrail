<div align="center">

# filegrail

**Local file provenance and metadata analysis.**

[![PyPI](https://img.shields.io/pypi/v/filegrail?style=flat-square&color=3775A9)](https://pypi.org/project/filegrail/)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square)
![68 formats](https://img.shields.io/badge/formats-68-8250df?style=flat-square)
![Runtime dependencies](https://img.shields.io/badge/runtime_dependencies-0-1f883d?style=flat-square)
![Local and read-only](https://img.shields.io/badge/local_%26_read--only-yes-1f883d?style=flat-square)
![Network requests](https://img.shields.io/badge/network_requests-none-1f883d?style=flat-square)
[![CI](https://github.com/osint-shifu/filegrail/actions/workflows/ci.yml/badge.svg)](https://github.com/osint-shifu/filegrail/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-Apache--2.0-8250df?style=flat-square)

[What it does](#what-it-does) ·
[Evidence sources](#evidence-sources) ·
[Formats](#supported-formats) ·
[Install](#installation) ·
[Usage](#usage) ·
[Examples](#examples)

</div>

---

`filegrail` analyzes files and directories using two kinds of information:

1. **Traces already stored on the machine** - browser downloads, OS origin metadata, shell history, archives, torrents, recent files, sync folders and trash records.
2. **Data stored inside the files** - EXIF, XMP, IPTC, C2PA, document properties, media metadata, email headers and other embedded metadata.

It keeps three questions separate:

| Area | Question |
|:---|:---|
| **Acquisition** | How did the file reach this machine? |
| **Intrinsic** | What does the file reveal about its own earlier history? |
| **Interaction** | What happened to the file after it arrived? |

Scanning is local, read-only and makes **no network requests**. `filegrail clean` is the only command that writes files, and it writes cleaned **copies** to a separate directory.

---

## What it does

| Capability | What you get |
|:---|:---|
| **File provenance** | Download URLs, referrers, browser records, OS origin attributes, archive/torrent membership, shell activity |
| **Metadata extraction** | Camera/device data, GPS, timestamps, authors, editors, software, document properties, media tags, C2PA and more |
| **Evidence correlation** | Agreement and conflicts between independent sources |
| **Timeline** | Acquisition, creation, editing and interaction events in chronological order |
| **Identifiers** | URLs, domains, email addresses, IPv4 addresses, coordinates and hashes |
| **File relationships** | XMP document IDs and derivation chains between related files |
| **Shared-source clustering** | Files grouped by camera body, camera model or author |
| **Comparison** | Metadata, provenance and timing differences between two files |
| **Explanation** | Every source behind a finding for one file |
| **Content search** | Identifiers extracted from supported document content with their location inside the file |
| **Metadata removal** | Cleaned copies of supported files, with verification of what remains |
| **JSON output** | Machine-readable results for scans and all commands |
| **Evidence coverage** | `doctor` shows which local evidence sources are available and how far back they reach |

---

## Evidence sources

### Acquisition and interaction traces

| Source | What `filegrail` can read |
|:---|:---|
| **Browser download history** | Download URL, referrer, time and recorded size from Chrome, Chromium, Brave, Edge, Vivaldi and Firefox profiles |
| **Windows `Zone.Identifier`** | `HostUrl`, `ReferrerUrl`, `ZoneId` |
| **macOS Where From** | Download URL and referrer stored in `kMDItemWhereFroms` |
| **macOS quarantine** | Download URL, referrer, downloading application and quarantine time |
| **Linux XDG attributes** | `user.xdg.origin.url` and `user.xdg.referrer.url` |
| **Archives** | Archive membership matched by file name and uncompressed size; archive origin can be inherited by extracted files |
| **Torrent files and client stores** | Torrent membership, trackers, client, comments, info hash/magnet data; local qBittorrent, Transmission and Deluge stores |
| **`yt-dlp` sidecars** | Page URL, uploader/channel, publication date, extractor and fetch time from `.info.json` |
| **Shell history** | Fetch commands such as `curl`, `wget`, `yt-dlp`, `scp`, `rsync`, `git`, `gh`, `aws` and others; non-fetch commands are recorded as later interaction |
| **Recent documents** | Linux desktop recent-file records |
| **Windows Recent shortcuts** | `.lnk` records showing that a file was opened |
| **Sync folders** | Nextcloud, Dropbox, Syncthing and OneDrive folder/account context |
| **Trash records** | Previous path and deletion time from the freedesktop trash |
| **Messenger file names** | WhatsApp and Telegram Desktop filename patterns; treated as weak evidence only |

Use:

```bash
filegrail doctor
```

to see which of these sources are actually available on the current machine or profile.

For another user profile or a mounted copy:

```bash
filegrail doctor --home /mnt/profile
filegrail /mnt/evidence --home /mnt/profile
```

---

## Supported formats

### Embedded metadata

| Metadata block | Extensions | Data extracted |
|:---|:---|:---|
| **EXIF** | `.jpg` `.jpeg` `.jpe` `.tif` `.tiff` `.dng` `.nef` `.cr2` `.arw` `.orf` `.rw2` `.webp` `.heic` `.heif` `.avif` | Camera make/model, body serial, lens, software, capture time, GPS |
| **PNG text** | `.png` `.apng` | `tEXt`, `zTXt`, `iTXt`: software, creation time, author and other stored values |
| **ISO BMFF** | `.mp4` `.m4v` `.mov` `.qt` `.3gp` `.m4a` `.heic` `.heif` `.avif` | Encoder/device, creation time, ISO 6709 location |
| **Matroska** | `.mkv` `.mk3d` `.webm` `.mka` | Writing application/library, segment date, tags |
| **RIFF/BWF** | `.wav` `.wave` `.rmi` `.avi` | `LIST/INFO`, recorder information, coding history, embedded ID3 where present |
| **Vorbis comments** | `.flac` `.ogg` `.oga` `.opus` `.spx` | Vendor string and all `NAME=value` comments |
| **ID3** | `.mp3` `.aac` `.tta` | Encoding software, artist, title, date and other ID3v2 frames |
| **PDF Info** | `.pdf` | PDF `Info` dictionary |
| **OOXML properties** | `.docx` `.docm` `.dotx` `.xlsx` `.xlsm` `.xltx` `.pptx` `.pptm` | Application, author, last editor, company, template, revision count, editing time |
| **OLE properties** | `.doc` `.dot` `.xls` `.xlt` `.ppt` `.pot` `.pps` `.msg` | Summary and document-summary properties |
| **OpenDocument metadata** | `.odt` `.ods` `.odp` `.odg` `.odf` `.ott` `.otp` | Generator, author, creation and editing metadata |
| **EPUB package** | `.epub` | OPF package metadata |
| **RTF metadata** | `.rtf` | Generator and `\info` fields |
| **SVG metadata** | `.svg` | Generator and embedded RDF metadata |
| **Jupyter notebook** | `.ipynb` | Kernel name and language runtime version |
| **C2PA** | `.jpg` `.jpeg` `.png` | Producing application, creation data, digital source type and hard-binding check |

### Cross-format metadata

These blocks are detected wherever they are embedded, not only by extension.

| Block | Typical data |
|:---|:---|
| **XMP** | Creating application, author, title, document IDs and derivation information |
| **XMP history** | Recorded editing steps and timestamps |
| **IPTC** | By-line, credit, source, copyright, headline, caption, keywords, place and creation date |

### Email

| Extension | Data extracted |
|:---|:---|
| `.eml` | Every `Received:` hop, connecting addresses and message headers |
| `.msg` | Transport headers where present, plus OLE document properties |

### Archives

| Extensions | What is read |
|:---|:---|
| `.zip` `.jar` `.whl` | Member names, sizes and metadata from supported files inside the archive |
| `.tar` `.tgz` `.gz` `.bz2` `.xz` | Members and supported metadata through the archive/compression layer |

Files inside supported archives are analyzed **without unpacking the archive to disk**.

### Torrents and sidecars

| File | Data extracted |
|:---|:---|
| `.torrent` | Trackers, creating client, comment, torrent membership and magnet/info-hash data |
| `<name>.info.json` | `yt-dlp` page URL, uploader/channel, publication date, extractor and fetch time |

For the complete format reference and edge cases, see [`docs/FORMATS.md`](docs/FORMATS.md).

---

## Content extraction

`--content` reads supported document text in addition to metadata and runs identifier extraction over it.

```bash
filegrail ./case --content
```

`--content` implies `--identify`.

| Extensions | Content read |
|:---|:---|
| `.txt` `.text` `.md` `.markdown` `.rst` `.log` | Text by line |
| `.csv` `.tsv` `.json` `.ndjson` `.jsonl` `.ipynb` `.yaml` `.yml` `.toml` `.ini` `.cfg` `.conf` `.vcf` `.ics` | Text/data by line |
| `.html` `.htm` `.xhtml` `.xml` `.svg` | Visible text and relevant URLs/attributes |
| `.docx` `.docm` `.dotx` | Body, footnotes, endnotes and comments |
| `.xlsx` `.xlsm` `.xltx` | Shared strings and inline cell text |
| `.pptx` `.pptm` | Slide text and notes |
| `.odt` `.ods` `.odp` `.odg` `.odf` `.ott` `.otp` | Document body, headers and footers |
| `.epub` | Chapters |
| `.eml` `.msg` | Decoded message body |

PDF **metadata** is supported, but PDF body text is not extracted by `--content`.

---

## Analysis

### Correlation and conflicts

`filegrail` compares independent evidence instead of collapsing everything into one origin field.

It can report:

- multiple sources supporting the same origin
- conflicting origin URLs
- file-size mismatches
- filename-only matches
- creation/modification dates in impossible order
- XMP editing steps out of sequence
- EXIF vs XMP differences
- PDF Info vs XMP differences
- XMP derivation relationships between files
- C2PA hard-binding mismatches

Confidence values rank competing claims. They are not probability scores or forensic verdicts.

### Investigation pivots

```bash
filegrail ./case --identify
```

Extracts:

- URLs
- domains
- email addresses
- IPv4 addresses
- coordinates
- MD5, SHA-1 and SHA-256 values found in metadata/content

Each value keeps the file, source and field/location it came from.

### Shared sources

```bash
filegrail ./photos --cluster
```

Groups files by:

- camera body/serial
- camera model
- author

### Timeline

```bash
filegrail ./case --timeline
```

Places recorded acquisition, creation, editing and interaction events in chronological order.

### File relationships

XMP identifiers such as:

- `xmpMM:DocumentID`
- `xmpMM:InstanceID`
- `xmpMM:OriginalDocumentID`
- `xmpMM:DerivedFrom`

can link renamed or exported files and show relationships such as derived-from, source-of, same-document or common-ancestor.

---

## Installation

Requires **Python 3.10+**.

```bash
pipx install filegrail
```

or:

```bash
uv tool install filegrail
```

From the repository:

```bash
git clone https://github.com/osint-shifu/filegrail.git
cd filegrail
PYTHONPATH=src python -m filegrail.cli /path/to/files
```

Runtime dependencies: **0**.

---

## Usage

```text
filegrail <path> [options]
filegrail <command> [options]
```

Analyze one file:

```bash
filegrail suspicious.pdf
```

Analyze a directory recursively:

```bash
filegrail ./evidence
```

Analyze the current directory:

```bash
filegrail .
```

Running `filegrail` with no arguments displays the command overview and does not start a scan.

### Commands

| Command | Purpose |
|:---|:---|
| `filegrail PATH` | Scan one file or directory |
| `filegrail scan PATH` | Explicit scan command |
| `filegrail explain FILE` | Show the evidence behind findings for one file |
| `filegrail compare A B` | Compare two files |
| `filegrail doctor` | Show available local evidence sources |
| `filegrail clean PATH --out DIR` | Write metadata-cleaned copies |
| `filegrail clean PATH --check` | Check what cleaning would remove without writing files |
| `filegrail menu` | Interactive command menu |
| `filegrail help COMMAND` | Command-specific help |

### Scan options

| Option | Purpose |
|:---|:---|
| `-v`, `--verbose` | Show every evidence record |
| `--brief` | Index only, without per-file detail |
| `--timeline` | Chronological event view |
| `--identify` | Extract investigation identifiers |
| `--content` | Also inspect supported document content; implies `--identify` |
| `--cluster` | Group files by shared cameras/authors |
| `--unknown-only` | Show only files with no findings |
| `--hash` | Compute SHA-256 for each file |
| `-j`, `--json` | JSON output |
| `--redact` | Redact credentials before printing |
| `--type NAME` | Filter by `archive`, `audio`, `document`, `image`, `mail`, `text` or `video` |
| `--ext LIST` | Filter by extensions, e.g. `--ext jpg,pdf` |
| `--limit N` | Limit files with no findings; `0` means all |
| `--home DIR` | Read evidence from another user profile |
| `--no-recurse` | Do not scan subdirectories |
| `--no-skip` | Include normally skipped build/cache/vendor directories |
| `--no-shell-history` | Disable shell-history correlation |
| `--no-archives` | Disable archive-origin inheritance |
| `--color` | Force ANSI color |
| `--no-color` | Disable ANSI color |

### Clean options

| Option | Purpose |
|:---|:---|
| `--out DIR` | Output directory for cleaned copies |
| `--check` | Check cleaning without writing files |
| `--overwrite` | Replace an existing destination file |
| `--type NAME` | Filter by file family |
| `--ext LIST` | Filter by extension |
| `--no-recurse` | Do not descend into subdirectories |
| `-j`, `--json` | JSON output |

---

## Examples

```bash
# Full analysis of one file
filegrail photo.jpg

# Scan a case and show only the index
filegrail ./case --brief

# Extract investigation pivots
filegrail ./case --identify

# Also search supported document content
filegrail ./case --content

# Build a timeline
filegrail ./case --timeline

# Find files sharing cameras or authors
filegrail ./case --cluster

# Explain exactly why a finding was produced
filegrail explain document.pdf

# Compare two files
filegrail compare original.docx edited.docx

# Analyze another user profile
filegrail /mnt/evidence --home /mnt/profile

# JSON report
filegrail ./case --json > report.json

# JSON report with credentials redacted
filegrail ./case --redact --json > report.json
```

---

## Example views

Real output, from real runs. A redirected report is laid out to 72 columns so it stays readable wherever it is opened later.

<details>
<summary><strong>One file</strong> &nbsp;·&nbsp; <code>filegrail holiday.jpg</code></summary>

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

Two claims about the same file, under the question each one answers. The meter says how directly a source knows what it claims — it is not a probability.

</details>

<details>
<summary><strong>A directory, index only</strong> &nbsp;·&nbsp; <code>filegrail ./case --brief</code></summary>

```text
  FILES                                                          4 files
  ──────────────────────────────────────────────────────────────────────

  ● chart.png               88 B                        png-text
  ● invoice.docx           498 B  XDG attribute         ooxml-properties
  ● press/holiday.jpg     3.4 MB  browser download      exif
  · notes.md                81 B  2026-09-05T20:15:16Z
```

A row a file: whatever needs a second look first, then the rest. A file nothing was found for carries its filesystem date instead of the columns it has nothing to put in them.

</details>

<details>
<summary><strong>Why a finding was produced</strong> &nbsp;·&nbsp; <code>filegrail explain holiday.jpg</code></summary>

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

The answer first, then what it rests on. A class with nothing in it says so rather than disappearing.

</details>

<details>
<summary><strong>Identifiers, including document content</strong> &nbsp;·&nbsp; <code>filegrail ./case --content</code></summary>

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
```

`both` means the value is in the document *and* in what the file records about itself. `recorded` is only the latter, `text` only the former.

</details>

<details>
<summary><strong>Checking before publishing</strong> &nbsp;·&nbsp; <code>filegrail clean ./case --check</code></summary>

```text
  nothing written

  ● chart.png                                                   png-text
  ● invoice.docx                                     document properties
  ● notes.md                                 no stripper for this format
  ● press/holiday.jpg                                               exif

  ──────────────────────────────────────────────────────────────────────
    4 files · 3 would be cleaned · 1 left alone
```

Exit code `0` if every copy would come out clean, `1` if any would not.

</details>

---

## Metadata removal

`filegrail clean` removes supported metadata from **copies**. Originals are never modified.

### Cleanable formats

| Family | Extensions |
|:---|:---|
| JPEG | `.jpg` `.jpeg` `.jpe` |
| PNG | `.png` `.apng` |
| ISO BMFF media | `.mp4` `.m4v` `.m4a` `.mov` `.qt` `.3gp` |
| Microsoft OOXML | `.docx` `.docm` `.dotx` `.xlsx` `.xlsm` `.xltx` `.pptx` `.pptm` |
| OpenDocument | `.odt` `.ods` `.odp` `.odg` `.ott` `.otp` |

Clean one file:

```bash
filegrail clean photo.jpg --out ./clean
```

Check without writing:

```bash
filegrail clean ./publish --check
```

After cleaning, the output is read again by the same metadata readers. Anything still detected is reported.

Metadata removal is **not anonymization**. Image pixels, sensor patterns, codec fingerprints and document content can still identify a source.

---

## JSON and automation

`--json` is available on all main commands.

Schemas include:

- `filegrail.scan/1`
- `filegrail.explain/1`
- `filegrail.compare/1`
- `filegrail.doctor/1`
- `filegrail.clean/1`

JSON output preserves:

- files and paths
- acquisition/intrinsic/interaction claims
- decoded metadata
- evidence sources
- confidence values
- findings and conflicts
- extracted identifiers
- shared-source clusters
- file relationships

---

## Privacy

`filegrail` makes **no network requests**.

Reports can contain sensitive local data such as:

- private URLs
- credentials or tokens embedded in URLs/commands
- file-system paths
- email addresses
- IP addresses
- GPS coordinates

Use:

```bash
filegrail ./case --redact
```

or:

```bash
filegrail ./case --redact --json
```

before sharing output.

Always review redacted reports manually before publishing them.

---

## Limits

- `filegrail` can only use evidence that still exists.
- Cleared browser history, removed extended attributes or missing shell history cannot be reconstructed.
- A supported sync folder can show account/folder context, but not who uploaded a file.
- WhatsApp/Telegram filename patterns do not identify a sender or conversation.
- C2PA hard binding is checked, but the certificate chain/signature trust is **not** verified.
- PDF metadata is read; PDF body text is not extracted by `--content`.
- Unsupported file formats can still participate in provenance analysis when external/local evidence about them exists.
- `filegrail` is not a monitoring agent, chain-of-custody system or full disk-forensics suite.

---

## Documentation

- [Complete format reference](docs/FORMATS.md)
- [Security](SECURITY.md)
- [Changelog](CHANGELOG.md)

---

## License

Apache-2.0.
