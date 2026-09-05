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

`filegrail` helps determine **where a file came from, what it contains about its own history, and what happened to it on the machine**.

It combines two sources of information:

1. **[Traces stored by the system and applications](#evidence-sources)** - browser download history, OS origin metadata, shell history, archives, torrents, recent-file records, sync folders and trash information. These traces can reveal where a file was downloaded from, which application handled it, when it appeared, where it was stored or whether it came from an archive or torrent.
2. **[Metadata stored inside the file](#supported-formats)** - EXIF, XMP, IPTC, C2PA, document properties, media tags, email headers and other embedded data. Depending on the format, this can reveal the device, software, author, editor, timestamps, GPS coordinates, document history and other details.

`filegrail` reports these findings in three separate areas:

| Area | Question |
|:---|:---|
| **Acquisition** | How did the file reach this machine? |
| **Intrinsic** | What does the file reveal about its own earlier history? |
| **Interaction** | What happened to the file after it arrived? |

Scanning is local, read-only and makes **no network requests**. `filegrail clean` is the only command that writes files, and it writes cleaned **copies** to a separate directory.

---

## What it does

Give `filegrail` a file or directory and it checks all supported provenance traces and embedded metadata that apply. Results always show **where each piece of information came from**.

If two independent sources disagree - for example, browser history and an OS origin attribute point to different URLs - both are shown and the conflict is reported instead of being silently resolved.

| Capability | What you get |
|:---|:---|
| **File provenance** | Where a file came from and when: the address it was fetched from, the page that linked to it, the program that fetched it, the archive or torrent it came in - and which source said so |
| **Metadata extraction** | What a file records about its own earlier life: camera and body serial, where and when it was taken, author and software, revision count - decoded field by field |
| **Evidence correlation** | Agreement and conflicts between independent sources |
| **Timeline** | Acquisition, creation, editing and interaction events in chronological order |
| **Identifiers** | [Six types](#identifier-types) of pivot, each with the file, source and place it came from |
| **File relationships** | XMP document IDs and derivation chains between related files |
| **Shared-source clustering** | Files grouped by camera body, camera model or author |
| **Comparison** | Metadata, provenance and timing differences between two files |
| **Explanation** | Every source behind a finding for one file |
| **Document text** | The same identifiers out of [document bodies](#document-content), with where in the document each one was |
| **Metadata removal** | Cleaned copies of supported files, with verification of what remains |
| **JSON output** | Machine-readable results for scans and all commands |
| **Evidence coverage** | `doctor` shows which local evidence sources are available and how far back they reach |

---

## Evidence sources

### Acquisition and interaction traces

These sources are **outside the analyzed file**. They are records left by the operating system, browser, shell and other applications while the file was downloaded, opened, copied, extracted, synchronized or deleted.

They can reveal URLs, referrers, download times, previous paths, archive or torrent membership and other information about how the file reached or moved through the machine. Availability depends on what data still exists on the system.

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

These are metadata fields stored **inside the file itself**. Depending on the format, `filegrail` can extract camera and device information, GPS coordinates, timestamps, authors and editors, creating software, document properties, media tags and authenticity metadata.

Field names are preserved as they appear in the original format, so the report shows the actual recorded metadata rather than simplified labels.

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

XMP, XMP history and IPTC can appear in several different file types. `filegrail` extracts them wherever those metadata blocks are supported, rather than treating them as belonging to one extension only.

| Block | Typical data |
|:---|:---|
| **XMP** | Creating application, author, title, document IDs and derivation information |
| **XMP history** | Recorded editing steps and timestamps |
| **IPTC** | By-line, credit, source, copyright, headline, caption, keywords, place and creation date |

### Email

For saved email messages, `filegrail` can reconstruct the recorded delivery path from `Received:` headers, including the servers and addresses involved in each hop.

With `--content`, it can also inspect the readable message body in `text/plain` and `text/html` parts.

| Extension | Data extracted |
|:---|:---|
| `.eml` | Every `Received:` hop, connecting addresses and message headers |
| `.msg` | Transport headers where present, plus OLE document properties |

### Archives

`filegrail` can inspect supported files **inside archives without unpacking the whole archive into the scanned directory**.

It also records archive membership and can match an extracted file back to an archive entry using its name and uncompressed size. If the archive itself has provenance information, that can help explain how the extracted file reached the machine.

| Extensions | What is read |
|:---|:---|
| `.zip` `.jar` `.whl` | Member names, sizes and metadata from supported files inside the archive |
| `.tar` `.tgz` `.gz` `.bz2` `.xz` | Members and supported metadata through the archive/compression layer |

### Torrents and sidecars

Torrent data can link a file to a `.torrent` when both the **file name and exact size** match an entry in the torrent.

For media downloaded with `yt-dlp`, a matching `<name>.info.json` sidecar can provide the original page URL, uploader or channel, publication date, extractor and download time.

| File | Data extracted |
|:---|:---|
| `.torrent` | Trackers, creating client, comment, torrent membership and magnet/info-hash data |
| `<name>.info.json` | `yt-dlp` page URL, uploader/channel, publication date, extractor and fetch time |

### Document content

`--content` extends the scan from metadata to the **actual text stored in supported documents**.

The full document text is not added to the report. `filegrail` extracts only supported identifiers - such as URLs, domains, email addresses, IP addresses, coordinates and hashes - and records exactly where each value was found.

Content scanning is limited to 1 MB of text per file and 64 members of a packaged document.

| Extensions | Content read | Place a value is reported with |
|:---|:---|:---|
| `.txt` `.text` `.md` `.markdown` `.rst` `.log` | Text by line | `line 12` |
| `.csv` `.tsv` `.json` `.ndjson` `.jsonl` `.ipynb` `.yaml` `.yml` `.toml` `.ini` `.cfg` `.conf` `.vcf` `.ics` | Text/data by line | `line 12` |
| `.html` `.htm` `.xhtml` `.xml` `.svg` | Visible text and relevant URLs/attributes | `line 12` |
| `.docx` `.docm` `.dotx` | Body, footnotes, endnotes and comments | `body`, `footnotes`, `endnotes`, `comments` |
| `.xlsx` `.xlsm` `.xltx` | Shared strings and inline cell text | `cell text`, `sheet 2` |
| `.pptx` `.pptm` | Slide text and notes | `slide 4`, `slide 4 notes` |
| `.odt` `.ods` `.odp` `.odg` `.odf` `.ott` `.otp` | Document body, headers and footers | `body`, `headers and footers` |
| `.epub` | Chapters | the chapter's own file name |
| `.eml` `.msg` | Decoded message body, every text part | `body`, `body (html)` |

PDF **metadata** is supported, but PDF body text is not extracted by `--content`.

### Identifier types

The same identifier detection is used for metadata and, with `--content`, document text. Filters remove common false positives such as software versions, file names that only look like domains and hexadecimal build identifiers.

| Type | Taken | Not taken |
|:---|:---|:---|
| `url` | `http` and `https` addresses, normalized | |
| `domain` | every host behind a URL or an address, and bare names whose TLD is a real one | anything shaped like a file name |
| `email` | addresses whose TLD is a real one | the address inside a message id - its host is still kept |
| `ipv4` | dotted quads, with private and reserved ranges marked as such | version numbers, and digits in a field naming software |
| `geo` | coordinates written with a hemisphere letter, a degree sign, a `geo:` URI, a map URL or an explicit latitude label | a bare pair of decimals, however many places it carries |
| `md5` `sha1` `sha256` | 32, 40 and 64 hex digits | digests in a field naming software, which are build ids |

Every extracted value includes the file, source and exact field or document location where it was found, so the result can be traced back to its context.

For the complete format reference and edge cases, see [`docs/FORMATS.md`](docs/FORMATS.md).

---

## Analysis

### Correlation and conflicts

When several sources describe the same file, `filegrail` compares them instead of choosing one answer automatically. Matching records can reinforce a finding; disagreements are shown as conflicts.

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

Each finding is also labeled by **how directly the source supports it**. This helps distinguish a browser record written during a download from metadata written by the file itself or a weaker filename-based match.

These labels describe the type and strength of the evidence. They are not probability scores or forensic verdicts:

| Word | The source | Written by |
|:---|:---|:---|
| `direct` | wrote the arrival down as it happened | browser history, Windows zone, macOS where-from and quarantine, XDG attributes, `yt-dlp` sidecars, mail delivery |
| `inherited` | says where the *container* came from, not the file | archive membership, torrents |
| `credentialed` | signed a manifest that travels with the file | C2PA |
| `self-reported` | is the file describing itself | EXIF, XMP, IPTC, document properties, media tags |
| `circumstantial` | was matched to the file rather than written for it | shell history, recent documents, sync folders, trash records |
| `weak` | is a naming convention and nothing more | messenger file names |

### Extracting investigation pivots from metadata and content

```bash
filegrail ./case --identify      # out of metadata
filegrail ./case --content       # out of metadata and document text
```

`--identify` extracts the [supported identifier types](#identifier-types) from metadata and provenance records.

`--content` does the same for the body of [supported documents](#document-content) and automatically enables identifier extraction.

Results show whether a value came from recorded metadata (`recorded`), document text (`text`) or appears in both (`both`).

### Shared sources

```bash
filegrail ./photos --cluster
```

Finds files that share the same recorded source information:

- **camera body/serial** - potentially the same physical camera
- **camera model** - the same device model, not necessarily the same unit
- **author** - the same recorded author value

### Timeline

```bash
filegrail ./case --timeline
```

Combines available timestamps from acquisition records, embedded metadata and later file interaction into one chronological view.

### File relationships

XMP identifiers such as:

- `xmpMM:DocumentID`
- `xmpMM:InstanceID`
- `xmpMM:OriginalDocumentID`
- `xmpMM:DerivedFrom`

can reveal relationships between files even after they have been renamed or exported. The scan can identify relationships such as derived-from, source-of, same-document and common-ancestor.

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

`filegrail PATH` is the normal scan command. `filegrail scan PATH` does the same thing explicitly.

Use `explain` when you want the evidence behind one file, `compare` for two files and `doctor` to check which provenance sources are available on the machine.

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

A normal scan checks embedded metadata and available local provenance traces. Additional work such as document-content inspection, SHA-256 hashing and clustering is enabled only when requested.

`--home` lets the same analysis use another user profile, copied profile or mounted system image as the source of local evidence.

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

Use `--out DIR` to write cleaned copies to another directory. Use `--check` to see what would be removed and whether anything would remain, without writing files.

The output directory cannot be inside the directory being cleaned.

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

# Also read the text inside supported documents
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

Below are examples of actual terminal output for the main workflows: scanning one file, scanning a directory, resolving conflicts, explaining evidence, building a timeline, extracting identifiers, clustering files, comparing files and checking evidence coverage.

<details>
<summary><strong>One file</strong> &nbsp;·&nbsp; <code>filegrail holiday.jpg</code></summary>

```text
  FILES IN DETAIL  ·  1 file
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

This view separates how the file arrived from what the file says about itself. The meter shows how directly each source supports the finding.

</details>

<details>
<summary><strong>A whole directory, top to bottom</strong> &nbsp;·&nbsp; <code>filegrail ./case</code></summary>

```text

    __ _ _                   _ _
   / _(_) |___ __ _ _ _ __ _(_) |
  |  _| | / -_) _` | '_/ _` | | |   filegrail 0.7.0
  |_| |_|_\___\__, |_| \__,_|_|_|
              |___/

  Trace where files came from. Extract what they reveal.

  target    ~/case
  profile   ~/home · another machine
  scanned   4 files · 4 types · 3.4 MB
  findings  3 files · 1 without findings

  ──────────────────────────────────────────────────────────────────────

  INVENTORY  ·  4 types
  ──────────────────────────────────────────────────────────────────────

    type  files    size
    ────  ─────  ──────
    JPEG      1  3.4 MB
    DOCX      1   834 B
    PNG       1    88 B
    MD        1    64 B

    2 images · 1 document · 1 text

  FINDINGS
  ──────────────────────────────────────────────────────────────────────

    what was found        files
    ────────────────────  ─────
    metadata                  3
    acquisition evidence      2
    authors / creators        1
    creating software         2
    device information        1
    coordinates               1
    timestamps                1

  NOTABLE FINDINGS
  ──────────────────────────────────────────────────────────────────────

    1 file contains coordinates
    6 unique identifiers extracted (--identify to list them)

  FILES  ·  4 files
  ──────────────────────────────────────────────────────────────────────
    ●  evidence found      !  needs a second look      ·  nothing found

    file                 size  how it arrived    what it says
    ────                 ────  ──────────────    ────────────
  ● chart.png            88 B  —                 PNG text
  ● invoice.docx        834 B  XDG attribute     OOXML properties
  ● press/holiday.jpg  3.4 MB  browser download  EXIF
  · notes.md             64 B  —                 last changed 2026-09-05

  FILES IN DETAIL  ·  3 files
  ──────────────────────────────────────────────────────────────────────

  ● invoice.docx                                                   834 B

  ACQUISITION  how the file reached this machine
  ← https://acme-legal.example/portal/invoice.docx
  │ XDG attribute · 2026-09-05T21:19:57Z                    ▰▰▰▰▱ direct

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

  METADATA SOURCES  ·  3 sources
  ──────────────────────────────────────────────────────────────────────

    reader            how directly it knows  files
    ────────────────  ─────────────────────  ─────
    PNG text          ▰▰▱▱▱  self-reported       1
    XDG attribute     ▰▰▰▰▱  direct              1
    browser download  ▰▰▰▰▱  direct              1

  ──────────────────────────────────────────────────────────────────────
    4 files analyzed · 3 with findings · 1 with no findings
```

A directory scan starts with a summary and file index, then shows detailed findings for each file and the evidence sources that produced them.

</details>

<details>
<summary><strong>Index only, for a large directory</strong> &nbsp;·&nbsp; <code>filegrail ./case --brief</code></summary>

```text
  FILES  ·  4 files
  ──────────────────────────────────────────────────────────────────────
    ●  evidence found      !  needs a second look      ·  nothing found

    file                 size  how it arrived    what it says
    ────                 ────  ──────────────    ────────────
  ● chart.png            88 B  —                 PNG text
  ● invoice.docx        834 B  XDG attribute     OOXML properties
  ● press/holiday.jpg  3.4 MB  browser download  EXIF
  · notes.md             64 B  —                 last changed 2026-09-05
```

`--brief` keeps the scan to one row per file. Files with no provenance or metadata findings are still listed.

</details>

<details>
<summary><strong>Two records that disagree</strong> &nbsp;·&nbsp; <code>filegrail ./contested</code></summary>

```text
  FILES IN DETAIL  ·  1 file
  ──────────────────────────────────────────────────────────────────────

  ! statement.pdf                                                   65 B

  ACQUISITION  how the file reached this machine
  ← https://documents.example.org/releases/statement.pdf
  │ browser download · chromium · 2026-08-31T10:49:33Z      ▰▰▰▰▱ direct
  │ referrer  https://documents.example.org/releases/
  │
  ← https://mail.example.net/attach/statement.pdf
  │ XDG attribute · 2026-09-05T21:19:57Z                    ▰▰▰▰▱ direct

  INTRINSIC  what the file records about its own earlier life
  ← made by LibreOffice 24.2
  │ PDF Info                                         ▰▰▱▱▱ self-reported
  │
  └ Producer  LibreOffice 24.2
  ! conflict
  │   browser download says
  │   https://documents.example.org/releases/statement.pdf
  │   XDG attribute says https://mail.example.net/attach/statement.pdf
```

When two independent records disagree, both remain visible and the report marks the conflict instead of choosing one automatically.

</details>

<details>
<summary><strong>Why a finding was produced</strong> &nbsp;·&nbsp; <code>filegrail explain holiday.jpg</code></summary>

```text

  filegrail  explain  holiday.jpg
  ──────────────────────────────────────────────────────────────────────

  profile   ~/home · another machine

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

`explain` shows the conclusion first, followed by the exact acquisition, intrinsic and interaction evidence behind it.

</details>

<details>
<summary><strong>Chronological events</strong> &nbsp;·&nbsp; <code>filegrail ./case --timeline</code></summary>

```text
  profile   ~/home · another machine

  2008-10-22 16:28:39  press/holiday.jpg
  │ made by NIKON COOLPIX P6000
  2026-08-31 10:49:33  press/holiday.jpg
  │ https://portal.example.org/press/2026/holiday-master.jpg
  2026-09-05 21:19:57  chart.png
  │ made by GIMP 2.10
  2026-09-05 21:19:57  invoice.docx
  │ https://acme-legal.example/portal/invoice.docx
  2026-09-05 21:19:57  invoice.docx
  │ self-reported metadata
  2026-09-05 21:19:57  notes.md
  │ (nothing found)
```

`--timeline` places all available dated events on one chronological axis, regardless of whether they came from provenance, metadata or later interaction.

</details>

<details>
<summary><strong>Identifiers, including document content</strong> &nbsp;·&nbsp; <code>filegrail ./case --content</code></summary>

```text
  IDENTIFIERS  ·  9 values
  ──────────────────────────────────────────────────────────────────────

  ● acme-legal.example                                     domain · both
  │ seen   2 occurrences in 1 file
  │ where  invoice.docx · url
  │        invoice.docx · body

  ● portal.example.org                                 domain · recorded
  │ seen   2 occurrences in 1 file
  │ where  holiday.jpg · url
  │        holiday.jpg · referrer

  ● innafirma.example                                      domain · text
  │ seen   1 occurrence in 1 file
  │ where  notes.md · line 1

  ● ann.shaw@acme-legal.example                             email · text
  │ seen   1 occurrence in 1 file
  │ where  invoice.docx · body

  ● kontakt@innafirma.example                               email · text
  │ seen   1 occurrence in 1 file
  │ where  notes.md · line 1

  ● 43.46745,11.88513                                     geo · recorded
  │ seen   1 occurrence in 1 file
  │ where  holiday.jpg · geo

  ● https://acme-legal.example/portal/invoice.docx        url · recorded
  │ seen   1 occurrence in 1 file
  │ where  invoice.docx · url

  ● https://portal.example.org/press                      url · recorded
  │ seen   1 occurrence in 1 file
  │ where  holiday.jpg · referrer

  ● https://portal.example.org/press/2026/holiday-master.jpg
  │ kind   url · recorded
  │ seen   1 occurrence in 1 file
  │ where  holiday.jpg · url
```

Identifier results show their origin: `recorded` for metadata or provenance, `text` for document content and `both` when the same value appears in both.

</details>

<details>
<summary><strong>Files sharing a camera or an author</strong> &nbsp;·&nbsp; <code>filegrail ./shots --cluster</code></summary>

```text
  SHARED SOURCES  ·  2 sources
  ──────────────────────────────────────────────────────────────────────

  ● 3001234                                        camera body · 3 files
  │ dune-01.jpg
  │ dune-02.jpg
  │ harbour.jpg

  ● NIKON COOLPIX P6000                           camera model · 3 files
  │ dune-01.jpg
  │ dune-02.jpg
  │ harbour.jpg
```

A shared camera serial can point to the same physical device. A shared camera model only shows that the files name the same model.

</details>

<details>
<summary><strong>Two files against each other</strong> &nbsp;·&nbsp; <code>filegrail compare beach.jpg beach-edited.jpg</code></summary>

```text

  filegrail  compare  beach.jpg · beach-edited.jpg
  ──────────────────────────────────────────────────────────────────────

  IDENTICAL

    Make              NIKON
    Model             COOLPIX P6000
    BodySerialNumber  3001234

  DIFFERING

    Software          NIKON COOLPIX P6000 vs Adobe Photoshop 26.1

  ARRIVED BY

    beach.jpg         no acquisition record
    beach-edited.jpg  no acquisition record

  CREATED

    apart             0 seconds

  ──────────────────────────────────────────────────────────────────────

  ASSESSMENT

    Both files agree on Make, Model, BodySerialNumber. How each one
    arrived is not established here.
```

</details>

<details>
<summary><strong>What this machine can answer at all</strong> &nbsp;·&nbsp; <code>filegrail doctor</code></summary>

```text

  filegrail  evidence sources
  ──────────────────────────────────────────────────────────────────────

  profile   ~/home · another machine

  Chromium family downloads  available
                               2 records across 1 of 1 profile
  Firefox downloads          unavailable
                               no profile found
  XDG origin attribute       available
                               written by KDE tools and wget --xattr,
                               but not by Firefox
  Mounted Zone.Identifier    available
                               user.Zone.Identifier on an NTFS mount
  Shell history              unavailable
                               no history file found
  Recent documents           unavailable
                               no list found
  macOS quarantine database  unavailable
                               no database in this profile
  Deleted files              unavailable
                               no trash directory
  Windows Recent shortcuts   unavailable
                               no Recent folder in this profile
  Torrent client stores      unavailable
                               no client store found
  Sync client folders        unavailable
                               no client configuration found
  Creation timestamps        available
                               statx
  C2PA signature check       unavailable
                               manifests are read and their hash
                               binding recomputed; validating the
                               certificate chain needs a crypto
                               library

  ──────────────────────────────────────────────────────────────────────

  HOW FAR BACK THE RECORDS REACH

  Chromium family oldest record  2026-08-31

  A file older than a source's oldest record cannot be resolved from
  it.
```

`doctor` distinguishes between a source that was available but contained no matching record and a source that was not available to search at all.

</details>

<details>
<summary><strong>Checking before publishing</strong> &nbsp;·&nbsp; <code>filegrail clean ./case --check</code></summary>

```text

  filegrail  clean  ~/case
  ──────────────────────────────────────────────────────────────────────

  nothing written

  ● chart.png                                                   PNG text
  ● invoice.docx                                     document properties
  ● notes.md                                 no stripper for this format
  ● press/holiday.jpg                                               EXIF

  ──────────────────────────────────────────────────────────────────────
    4 files · 3 would be cleaned · 1 left alone
```

Exit code `0` if every copy would come out clean, `1` if any would not.

</details>

---

## Metadata removal

`filegrail clean` removes supported metadata from **copies**. Originals are never modified.

### Cleanable formats

Only the formats listed below can be cleaned. Unsupported files are left unchanged and reported as such.

Cleaned files are written as separate copies. The originals are never modified.

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

After cleaning, `filegrail` scans each copy again. If supported metadata is still detectable, it is reported instead of being treated as successfully removed.

Metadata removal is **not anonymization**. Image pixels, sensor patterns, codec fingerprints and document content can still identify a source.

---

## JSON and automation

Use `--json` when results need to be processed by scripts, `jq`, notebooks, pipelines or other tools. All main commands support machine-readable output with command-specific schemas and exit codes.

Schemas:

- `filegrail.scan/1`
- `filegrail.explain/1`
- `filegrail.compare/1`
- `filegrail.doctor/1`
- `filegrail.clean/1`

What a script gets back:

| Code | Meaning |
|:---|:---|
| `0` | The command ran. For `clean` and `clean --check`, every copy came out clean |
| `1` | `clean` only: metadata survived in at least one copy, or would |
| `2` | The command was asked for something it cannot do - a missing path, two arguments where one file was needed, an unknown option |

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

`filegrail` performs analysis locally and makes **no network requests**. The main privacy risk is therefore the report itself, which may contain sensitive information recovered from local files and system traces.

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

Read a redacted report yourself before you publish it.

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
