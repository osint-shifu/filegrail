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

`filegrail` helps determine **where a file came from, what it contains about its own history, what it says inside, and what happened to it on the machine**.

It combines three sources of information:

1. **[Origin - what the machine recorded](#evidence-sources)** - browser download history, OS origin metadata, shell history, archives, torrents, recent-file records, sync folders and trash information. These traces can reveal where a file was downloaded from, which application handled it, when it appeared, where it was stored or whether it came from an archive or torrent.
2. **[Metadata - what the file records about itself](#supported-formats)** - EXIF, XMP, IPTC, C2PA, document properties, media tags, email headers and other embedded data. Depending on the format, this can reveal the device, software, author, editor, timestamps, GPS coordinates, document history and other details.
3. **[Content - what the file says inside](#document-content)** - with `--content`, the readable text of supported documents is scanned as well: the body of a letter, the notes on a slide, the cells of a spreadsheet, the decoded body of a message. That text is run through the same **identifier extraction** as everything above - URLs, domains, email addresses, IP addresses, coordinates and MD5/SHA-1/SHA-256 values - so an address written in a letter can be matched against the address the file was fetched from. The text itself is never printed or stored; what is kept is each identifier and where in the document it was found.

Those are the three places `filegrail` looks. What it finds there is filed under one of three categories, which is a different question - a shell command that fetched a file and a shell command that merely opened it come from the same place and say different things:

| Category | Question | Examples |
|:---|:---|:---|
| **Origin** | How or from where did the file reach this environment? | Browser download history, `Zone.Identifier`, macOS where-from, XDG attributes, a fetch command, a `yt-dlp` sidecar |
| **Metadata** | What does the file record about itself? | EXIF, XMP, IPTC, document properties, media tags, Content Credentials |
| **Activity** | What happened to the file here? | Recent Documents, Windows shortcuts, trash records, sync folders, filesystem times |

Each record also carries **how it was matched to that file** - a recorded path, a file name, a name and exact size, membership of a container, or the file's own bytes. A record tied to a file by nothing but its name is reported as exactly that.

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
| **Timeline** | Origin, creation, editing and activity events in chronological order |
| **Identifiers** | [Six types](#identifier-types) of pivot, each with the file, source and place it came from |
| **File relationships** | XMP document IDs and derivation chains between related files |
| **Clusters** | Files grouped by camera serial, camera model or author, with the field each grouping rests on |
| **Comparison** | Metadata, provenance and timing differences between two files |
| **Explanation** | Every source behind a finding for one file |
| **Document text** | The same identifiers out of [document bodies](#document-content), with where in the document each one was |
| **Metadata removal** | Cleaned copies of supported files, with verification of what remains |
| **JSON output** | Machine-readable results for scans and all commands |
| **Evidence coverage** | `doctor` shows which local evidence sources are available and how far back they reach |

---

## Evidence sources

### Origin and activity traces

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
| **Shell history** | Fetch commands such as `curl`, `wget`, `yt-dlp`, `scp`, `rsync`, `git`, `gh`, `aws` and others; non-fetch commands are recorded as activity |
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

### How a record was matched to a file

Every record says how it came to be about the file it is reported under. A download row found by the path it was saved to and one found by a name that happens to be the same are not equally firm, and the report never leaves that to be guessed.

These are the words the report prints in its `match` column and the values `--json` writes under `match.method`.

| Basis | What it means | Where it comes from |
|:---|:---|:---|
| `embedded` | Decoded out of the file's own bytes | EXIF, XMP, IPTC, document properties, Content Credentials, mail headers |
| `file-attribute` | Read from what the filesystem keeps for this exact file | `Zone.Identifier`, macOS where-from, XDG attributes, creation times |
| `recorded-path` | An external store names this exact path | Browser download history, Recent Documents |
| `sidecar` | A separate file written next to it and naming it | `yt-dlp` sidecar, freedesktop trash record |
| `name+size` | Both agree; two files can share both, but not easily | Torrents, archive members, Windows shortcuts |
| `filename` | The name is all that matched | A download record for a file that has since moved, a messenger naming pattern |
| `container-member` | Read from a member, or inherited from the container | Archives |
| `sync-root` | The file lies under a folder a client manages | Nextcloud, Dropbox, Syncthing, OneDrive |

`filegrail` does not put a number on how much a record is worth. There is no probability behind such a number and no forensic basis for one; what it reports instead is the category, the source and the basis of the match, which are facts.

### Extracting investigation pivots from metadata and content

```bash
filegrail ./case --identify      # out of metadata
filegrail ./case --content       # out of metadata and document text
```

`--identify` extracts the [supported identifier types](#identifier-types) from metadata and provenance records.

`--content` does the same for the body of [supported documents](#document-content) and automatically enables identifier extraction.

Values are grouped by type - urls, domains, emails, ip addresses, coordinates, hashes - one row per place a value was seen, with the file, the source and the field or location it came from. A value seen under more than one source gets a section of its own at the end: an address written in a document *and* recorded in how the file arrived is the pairing reading content exists to find.

### Clusters

```bash
filegrail ./photos --cluster
```

Finds files that share an identifying value, and says which field the grouping rests on:

- **camera serial** - `EXIF · BodySerialNumber`. A serial is assigned per unit, so the same one is the same physical camera.
- **camera model** - `EXIF · Make + Model`. A product line thousands of people own, which is not the same claim.
- **author** - `OOXML · creator` or the equivalent. A name somebody typed.

### Timeline

```bash
filegrail ./case --timeline
```

Combines available timestamps from origin records, embedded metadata and later activity into one chronological view.

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
| `--unknown-only` | Show only files with no evidence found |
| `--hash` | Compute SHA-256 for each file |
| `-j`, `--json` | JSON output |
| `--redact` | Redact credentials before printing |
| `--type NAME` | Filter by `archive`, `audio`, `document`, `image`, `mail`, `text` or `video` |
| `--ext LIST` | Filter by extensions, e.g. `--ext jpg,pdf` |
| `--limit N` | Limit files with no evidence found; `0` means all |
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
filegrail 0.8.1
────────────────────────────────────────────────────────────────────────
target    ~/case/press/holiday.jpg · profile ~/home · external

FILE  ·  holiday.jpg · JPEG · 3.4 MB
────────────────────────────────────────────────────────────────────────

  path    /home/oryon/case/press/holiday.jpg
  mtime   2026-09-06 00:53:31

ORIGIN  ·  1 record
────────────────────────────────────────────────────────────────────────

  source             match          time
  ─────────────────  ─────────────  ───────────────────
› Chromium download  recorded-path  2026-08-31 10:49:33
  │ url       https://portal.example.org/press/2026/holiday-master.jpg
  └ referrer  https://portal.example.org/press/

METADATA  ·  1 source · 8 fields
────────────────────────────────────────────────────────────────────────

  source  summary
  ──────  ──────────────────────────────────────────────────────────────
› EXIF    NIKON COOLPIX P6000 · serial 3001234 · 43.467447, 11.885128 ·
          2008-10-22 16:28:39

EXIF  ·  8 fields
────────────────────────────────────────────────────────────────────────

  field             value
  ────────────────  ───────────────────
  Make              NIKON
  Model             COOLPIX P6000
  DateTimeOriginal  2008:10:22 16:28:39
  BodySerialNumber  3001234
  GPSLatitudeRef    N
  GPSLatitude       43, 28, 2.81
  GPSLongitudeRef   E
  GPSLongitude      11, 53, 6.46
```

One section per question, and every record says how it was tied to this file - `recorded-path` is a store naming this exact path, `embedded` is the file's own bytes. Each metadata block then gets a table of its own, field by field.

</details>

<details>
<summary><strong>A whole directory, top to bottom</strong> &nbsp;·&nbsp; <code>filegrail ./case</code></summary>

```text
filegrail 0.8.1
────────────────────────────────────────────────────────────────────────
target    ~/case · profile ~/home · external

SUMMARY  ·  4 files · 4 types · 3.4 MB
────────────────────────────────────────────────────────────────────────

  with evidence      3
  unresolved         1
  origin records     2
  metadata sources   3
  activity records   0
  findings           0

FILES  ·  4 files · 4 types · 3.4 MB
────────────────────────────────────────────────────────────────────────

  file               type  size    origin             metadata
  ─────────────────  ────  ──────  ─────────────────  ────────────────
  press/holiday.jpg  JPEG  3.4 MB  Chromium download  EXIF
  invoice.docx       DOCX  834 B   XDG attribute      OOXML properties
  chart.png          PNG   88 B    —                  PNG text
· notes.md           MD    64 B    —                  —

  · no evidence found

ORIGIN  ·  2 records · 2 files
────────────────────────────────────────────────────────────────────────

  file            source             match           time
  ──────────────  ─────────────────  ──────────────  ───────────────────
› press/holiday.  Chromium download  recorded-path   2026-08-31 10:49:33
  jpg
  │ url       https://portal.example.org/press/2026/holiday-master.jpg
  └ referrer  https://portal.example.org/press/
› invoice.docx    XDG attribute      file-attribute  —
  └ url  https://acme-legal.example/portal/invoice.docx

METADATA  ·  3 sources · 3 files
────────────────────────────────────────────────────────────────────────

  file               source            summary
  ─────────────────  ────────────────  ─────────────────────────────────
› press/holiday.jpg  EXIF              NIKON COOLPIX P6000 · serial
                                       3001234 · 43.467447, 11.885128 ·
                                       2008-10-22 16:28:39
› invoice.docx       OOXML properties  Ann Shaw
› chart.png          PNG text          GIMP 2.10

UNRESOLVED  ·  1 file
────────────────────────────────────────────────────────────────────────

  file          type  size  last modified
  ────────────  ────  ────  ───────────────────
· notes.md      MD    64 B  2026-09-06 00:53:31

SCAN GAPS  ·  1 item
────────────────────────────────────────────────────────────────────────

  what             detail
  ───────────────  ───────────────────────────────────
· browser history  2 download records across 1 profile
```

Counts first, then a row per file, then the records themselves grouped by the question each one answers. The counts in a heading are always of the rows underneath it. Files nothing explained get their own section at the end.

</details>

<details>
<summary><strong>Index only, for a large directory</strong> &nbsp;·&nbsp; <code>filegrail ./case --brief</code></summary>

```text
filegrail 0.8.1 · brief
────────────────────────────────────────────────────────────────────────
target    ~/case · profile ~/home · external

SUMMARY  ·  4 files · 4 types · 3.4 MB
────────────────────────────────────────────────────────────────────────

  with evidence   3
  unresolved      1
  needs review    0

FILES  ·  4 files · 4 types · 3.4 MB
────────────────────────────────────────────────────────────────────────

  file               type  size    origin             metadata
  ─────────────────  ────  ──────  ─────────────────  ────────────────
  press/holiday.jpg  JPEG  3.4 MB  Chromium download  EXIF
  invoice.docx       DOCX  834 B   XDG attribute      OOXML properties
  chart.png          PNG   88 B    —                  PNG text
· notes.md           MD    64 B    —                  —

  · no evidence found
```

`--brief` stops after the table of files. A file nothing was found for is still listed, marked `·`, because *no evidence found* is a result and not an omission.

</details>

<details>
<summary><strong>Two records that disagree</strong> &nbsp;·&nbsp; <code>filegrail ./contested</code></summary>

```text
filegrail 0.8.1
────────────────────────────────────────────────────────────────────────
target    ~/contested/statement.pdf · profile ~/home · external

FILE  ·  statement.pdf · PDF · 65 B
────────────────────────────────────────────────────────────────────────

  path    /home/oryon/contested/statement.pdf
  mtime   2026-09-06 00:53:31

ORIGIN  ·  2 records
────────────────────────────────────────────────────────────────────────

  source             match           time
  ─────────────────  ──────────────  ───────────────────
› Chromium download  recorded-path   2026-08-31 10:49:33
  │ url       https://documents.example.org/releases/statement.pdf
  └ referrer  https://documents.example.org/releases/
› XDG attribute      file-attribute  —
  └ url  https://mail.example.net/attach/statement.pdf

METADATA  ·  1 source · 1 field
────────────────────────────────────────────────────────────────────────

  source    summary
  ────────  ────────────────
› PDF Info  LibreOffice 24.2

FINDINGS  ·  2 findings · 2 needs review
────────────────────────────────────────────────────────────────────────

  type             file           field       sources
  ───────────────  ─────────────  ──────────  ───────
! source conflict  statement.pdf  origin URL  —
  └   browser download says
      https://documents.example.org/releases/statement.pdf
! source conflict  statement.pdf  origin URL  —
  └   XDG attribute says https://mail.example.net/attach/statement.pdf

  ! needs review

PDF INFO  ·  1 field
────────────────────────────────────────────────────────────────────────

  field         value
  ────────────  ────────────────
  Producer      LibreOffice 24.2
```

Both records stay visible and neither is promoted. The disagreement is a row in `FINDINGS`, with the field it is about and the two values under it, and the file carries `!` in the table above - once, not in every section it appears in.

</details>

<details>
<summary><strong>Why a finding was produced</strong> &nbsp;·&nbsp; <code>filegrail explain holiday.jpg</code></summary>

```text
filegrail 0.8.1 · explain
────────────────────────────────────────────────────────────────────────
target    ~/case/press/holiday.jpg · profile ~/home · external

SUMMARY  ·  2 evidence records
────────────────────────────────────────────────────────────────────────

  origin records     1
  metadata sources   1
  activity records   0
  correlation        0

ORIGIN  ·  1 record
────────────────────────────────────────────────────────────────────────

  source             match          time
  ─────────────────  ─────────────  ───────────────────
› Chromium download  recorded-path  2026-08-31 10:49:33
  │ url       https://portal.example.org/press/2026/holiday-master.jpg
  └ referrer  https://portal.example.org/press/

METADATA  ·  1 source · 8 fields
────────────────────────────────────────────────────────────────────────

  source  summary
  ──────  ──────────────────────────────────────────────────────────────
› EXIF    NIKON COOLPIX P6000 · serial 3001234 · 43.467447, 11.885128 ·
          2008-10-22 16:28:39

EXIF  ·  8 fields
────────────────────────────────────────────────────────────────────────

  field             value
  ────────────────  ───────────────────
  Make              NIKON
  Model             COOLPIX P6000
  DateTimeOriginal  2008:10:22 16:28:39
  BodySerialNumber  3001234
  GPSLatitudeRef    N
  GPSLatitude       43, 28, 2.81
  GPSLongitudeRef   E
  GPSLongitude      11, 53, 6.46
```

`explain` shows the material: what was found, where each record came from, how it was matched, and what correlation made of them. The prose assessment is in `--json`.

</details>

<details>
<summary><strong>Chronological events</strong> &nbsp;·&nbsp; <code>filegrail ./case --timeline</code></summary>

```text
filegrail 0.8.1 · timeline
────────────────────────────────────────────────────────────────────────
target    ~/case · profile ~/home · external

TIMELINE  ·  2 events · 1 file
────────────────────────────────────────────────────────────────────────

  time                 file               source             event
  ───────────────────  ─────────────────  ─────────────────  ──────────
  2008-10-22 16:28:39  press/holiday.jpg  EXIF               captured
  2026-08-31 10:49:33  press/holiday.jpg  Chromium download  downloaded
```

Every dated record on one axis, each saying what happened: captured, downloaded, delivered, extracted, opened, deleted. A file nothing dated is not an event and does not appear - nothing happened at a time nobody recorded.

</details>

<details>
<summary><strong>Identifiers, including document content</strong> &nbsp;·&nbsp; <code>filegrail ./case --content</code></summary>

```text
IDENTIFIERS  ·  9 unique values · 11 occurrences · 1 cross-source
────────────────────────────────────────────────────────────────────────

URLS  ·  3 unique values · 3 occurrences
────────────────────────────────────────────────────────────────────────

› https://acme-legal.example/portal/invoice.docx
  │ file    invoice.docx
  │ source  XDG attribute
  └ where   url
› https://portal.example.org/press
  │ file    holiday.jpg
  │ source  browser download
  └ where   referrer
› https://portal.example.org/press/2026/holiday-master.jpg
  │ file    holiday.jpg
  │ source  browser download
  └ where   url

DOMAINS  ·  3 unique values · 5 occurrences
────────────────────────────────────────────────────────────────────────

  value               file          source            field / location
  ──────────────────  ────────────  ────────────────  ────────────────
  acme-legal.example  invoice.docx  XDG attribute     url
  acme-legal.example  invoice.docx  content           body
  portal.example.org  holiday.jpg   browser download  url
  portal.example.org  holiday.jpg   browser download  referrer
  innafirma.example   notes.md      content           line 1

EMAILS  ·  2 unique values · 2 occurrences
────────────────────────────────────────────────────────────────────────

  value                        file          source   field / location
  ───────────────────────────  ────────────  ───────  ────────────────
  ann.shaw@acme-legal.example  invoice.docx  content  body
  kontakt@innafirma.example    notes.md      content  line 1

COORDINATES  ·  1 unique value · 1 occurrence
────────────────────────────────────────────────────────────────────────

  value              file         source           field / location
  ─────────────────  ───────────  ───────────────  ────────────────
  43.46745,11.88513  holiday.jpg  device metadata  geo

CROSS-SOURCE MATCHES  ·  1 value
────────────────────────────────────────────────────────────────────────

  value               sources                  files
  ──────────────────  ───────────────────────  ────────────
  acme-legal.example  XDG attribute · content  invoice.docx

UNRESOLVED  ·  1 file
────────────────────────────────────────────────────────────────────────

  file          type  size  last modified
  ────────────  ────  ────  ───────────────────
· notes.md      MD    64 B  2026-09-06 00:53:31

SCAN GAPS  ·  1 item
────────────────────────────────────────────────────────────────────────

  what             detail
  ───────────────  ───────────────────────────────────
· browser history  2 download records across 1 profile
```

One section per type, one row per place a value was seen, with the file, the source and the field it came from. A URL too long for those columns takes the line. Values seen under more than one source get a section of their own at the end.

</details>

<details>
<summary><strong>Files sharing a camera or an author</strong> &nbsp;·&nbsp; <code>filegrail ./shots --cluster</code></summary>

```text
CLUSTERS  ·  2 groups · 3 files
────────────────────────────────────────────────────────────────────────

  attribute      value                files  basis
  ─────────────  ───────────────────  ─────  ───────────────────────
› camera serial  3001234                  3  EXIF · BodySerialNumber
  │ dune-01.jpg
  │ dune-02.jpg
  └ harbour.jpg
› camera model   NIKON COOLPIX P6000      3  EXIF · Make + Model
  │ dune-01.jpg
  │ dune-02.jpg
  └ harbour.jpg
```

Each cluster says which field it rests on. `EXIF · BodySerialNumber` is one physical camera, because a serial is assigned per unit; `EXIF · Make + Model` is a product line thousands of people own, which is not the same claim.

</details>

<details>
<summary><strong>Two files against each other</strong> &nbsp;·&nbsp; <code>filegrail compare beach.jpg beach-edited.jpg</code></summary>

```text
filegrail 0.8.1 · compare
────────────────────────────────────────────────────────────────────────
left      /home/oryon/beach.jpg
right     /home/oryon/beach-edited.jpg

FILES  ·  2 files
────────────────────────────────────────────────────────────────────────

  field         beach.jpg  beach-edited.jpg
  ────────────  ─────────  ────────────────
  type          JPEG       JPEG
  size          335 B      368 B

METADATA  ·  4 compared fields
────────────────────────────────────────────────────────────────────────

  field             beach.jpg            beach-edited.jpg
  ────────────────  ───────────────────  ────────────────────
  Make              NIKON                NIKON
  Model             COOLPIX P6000        COOLPIX P6000
  BodySerialNumber  3001234              3001234
  Software          NIKON COOLPIX P6000  Adobe Photoshop 26.1

ORIGIN  ·  2 records
────────────────────────────────────────────────────────────────────────

  file              source
  ────────────────  ────────────────
  beach.jpg         no origin record
  beach-edited.jpg  no origin record

CORRELATION  ·  5 results
────────────────────────────────────────────────────────────────────────

  result      field             value
  ──────────  ────────────────  ────────────────────────────────────────
  match       Make              NIKON
  match       Model             COOLPIX P6000
  match       BodySerialNumber  3001234
! difference  Software          NIKON COOLPIX P6000 ≠ Adobe Photoshop
                                26.1
  interval    created           0 seconds apart

RELATIONSHIPS  ·  1 relation
────────────────────────────────────────────────────────────────────────

  relationship  files                         basis
  ────────────  ────────────────────────────  ────────────────────────
  same device   beach.jpg · beach-edited.jpg  BodySerialNumber 3001234
```

`METADATA` shows the values side by side and decides nothing about them; `CORRELATION` says what follows. A relationship is what several fields agreeing amount to - one body serial in both files is one physical camera, which is a stronger statement than any single row above it.

</details>

<details>
<summary><strong>What this machine can answer at all</strong> &nbsp;·&nbsp; <code>filegrail doctor</code></summary>

```text
filegrail 0.8.1 · doctor
────────────────────────────────────────────────────────────────────────
profile   ~/home · external

SUMMARY  ·  13 sources
────────────────────────────────────────────────────────────────────────

  available     4
  partial       1
  unavailable   8

SOURCES  ·  13 sources · 4 available · 1 partial · 8 unavailable
────────────────────────────────────────────────────────────────────────

  source                     type        status       coverage / detail
  ─────────────────────────  ──────────  ───────────  ──────────────────
  Chromium family downloads  artifact    available    2 records across 1
                                                      of 1 profile
  Firefox downloads          artifact    unavailable  no profile found
  XDG origin attribute       artifact    available    written by KDE
                                                      tools and wget
                                                      --xattr, but not
                                                      by Firefox
  Mounted Zone.Identifier    artifact    available    user.Zone.Identifi
                                                      er on an NTFS
                                                      mount
  Shell history              artifact    unavailable  no history file
                                                      found
  Recent documents           artifact    unavailable  no list found
  macOS quarantine database  artifact    unavailable  no database in
                                                      this profile
  Deleted files              artifact    unavailable  no trash directory
  Windows Recent shortcuts   artifact    unavailable  no Recent folder
                                                      in this profile
  Torrent client stores      artifact    unavailable  no client store
                                                      found
  Sync client folders        artifact    unavailable  no client
                                                      configuration
                                                      found
  Creation timestamps        filesystem  available    statx
  C2PA signature check       parser      partial      manifests are read
                                                      and their hash
                                                      binding
                                                      recomputed;
                                                      validating the
                                                      certificate chain
                                                      needs a crypto
                                                      library

LIMITATIONS  ·  2 items
────────────────────────────────────────────────────────────────────────

  source                  limitation
  ──────────────────────  ──────────────────────────────────────────────
  Chromium family record  no record before 2026-08-31
  C2PA signature check    manifests are read and their hash binding
                          recomputed; validating the certificate chain
                          needs a crypto library
```

`available` here is the technical reach of a source, not a judgement about evidence: a source that was available and held nothing has answered, and one that was unavailable never got the question. `LIMITATIONS` says how far back the ones that answered can reach.

</details>

<details>
<summary><strong>Checking before publishing</strong> &nbsp;·&nbsp; <code>filegrail clean ./case --check</code></summary>

```text
filegrail 0.8.1 · clean --check
────────────────────────────────────────────────────────────────────────
target    ~/case
mode      check only · nothing written

SUMMARY  ·  4 files
────────────────────────────────────────────────────────────────────────

  cleanable      3
  unsupported    1
  would remain   0
  exit           0

RESULTS  ·  4 files · 3 cleanable · 1 unsupported
────────────────────────────────────────────────────────────────────────

  file               format  metadata             result
  ─────────────────  ──────  ───────────────────  ───────────
  chart.png          PNG     PNG text             would clean
  invoice.docx       DOCX    document properties  would clean
  notes.md           MD      —                    unsupported
  press/holiday.jpg  JPEG    EXIF                 would clean
```

The summary prints the exit code: `0` if every copy would come out clean, `1` if any would not. Anything the readers can still see in a copy gets its own section.

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

Each document carries its own schema version. A number moves only when a field in *that* document changes meaning or leaves, so a consumer of `clean` is not sent to read a diff with nothing in it because the vocabulary around it changed.

| Schema | Since | What changed |
|:---|:---|:---|
| `filegrail.scan/2` | 0.8.0 | `files[].origins` became `files[].evidence`; every record carries `category` and `match`; `confidence` is gone; `reconciliation` is `correlation` |
| `filegrail.explain/2` | 0.8.0 | the same file document, and `conclusion` became `assessment` |
| `filegrail.compare/2` | 0.8.0 | `acquisition` became `origin` |
| `filegrail.doctor/1` | 0.3.0 | |
| `filegrail.clean/1` | 0.4.0 | |

What a script gets back:

| Code | Meaning |
|:---|:---|
| `0` | The command ran. For `clean` and `clean --check`, every copy came out clean |
| `1` | `clean` only: metadata survived in at least one copy, or would |
| `2` | The command was asked for something it cannot do - a missing path, two arguments where one file was needed, an unknown option |

A scan document holds `root`, `home`, `summary`, `files`, and - when asked for - `identifiers`, `shared_attributes` and `unsearched`. Each file holds `path`, `size`, `mtime`, `btime`, `sha256`, `links`, and `evidence`: one entry per record, each with its `category`, its `source`, the `match` that tied it to the file, and the fields the parser decoded. Correlation results ride on the file as `correlation`.

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
