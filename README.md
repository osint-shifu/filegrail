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

`filegrail` helps determine **where a file came from, what it records about itself, what it contains, and what happened to it locally**.

It draws from three areas:

1. **[Origin - what the machine recorded](#evidence-sources)** - browser history, OS origin metadata, shell history, archives, torrents, recent-file records, sync folders and trash. These traces can reveal where a file came from, how it arrived, when it appeared and where it was stored.
2. **[Metadata - what the file records about itself](#supported-formats)** - EXIF, XMP, IPTC, C2PA, document properties, media tags, email headers and other embedded data. This can reveal devices, software, authors, timestamps, GPS coordinates and document history.
3. **[Content - what the file says inside](#document-content)** - with `--content`, readable text from supported documents is scanned for URLs, domains, email addresses, IP addresses, coordinates and MD5/SHA-1/SHA-256 values. The text itself is not printed or stored - only extracted identifiers and their locations.

Where evidence was found and what that evidence means are kept separate:

| Category | Question | Examples |
|:---|:---|:---|
| **Origin** | How or from where did the file reach this environment? | Browser download history, `Zone.Identifier`, macOS where-from, XDG attributes, a fetch command, a `yt-dlp` sidecar |
| **Metadata** | What does the file record about itself? | EXIF, XMP, IPTC, document properties, media tags, Content Credentials |
| **Activity** | What happened to the file here? | Recent Documents, Windows shortcuts, trash records, sync folders, filesystem times |

Every record also states **how it was matched to the file** - by exact path, file attribute, name and size, container membership, filename or the file's own bytes.

Scanning is local, read-only and makes **no network requests**. `filegrail clean` is the only command that writes files, and it writes cleaned **copies** to a separate directory.

---

## What it does

Give `filegrail` a file or directory and it checks the provenance traces and embedded metadata that apply. Every result keeps its source visible.

When independent sources disagree, both values are preserved and the conflict is reported rather than resolved automatically.

| Capability | What you get |
|:---|:---|
| **File provenance** | Where and how a file arrived, when it appeared and which source recorded it |
| **Metadata extraction** | Device, software, author, timestamps, GPS, revision data and other embedded fields |
| **Evidence correlation** | Agreements and conflicts between independent sources |
| **Timeline** | Origin, creation, editing and activity events in chronological order |
| **Identifiers** | [Supported types](#identifier-types) of investigation pivot with file, source and location |
| **File relationships** | XMP document IDs and derivation chains between related files |
| **Clusters** | Files grouped by shared camera serial, camera model or author |
| **Comparison** | Metadata, provenance and timing differences between two files |
| **Explanation** | Evidence behind findings for one file |
| **Document text** | Identifiers extracted from [document bodies](#document-content) with their locations |
| **Metadata removal** | Cleaned copies of supported files with post-clean verification |
| **JSON output** | Machine-readable results for scans and all commands |
| **Evidence coverage** | `doctor` shows available local evidence sources and their coverage |

---

## Evidence sources

### Origin and activity traces

These sources exist **outside the analyzed file**. They are records left by browsers, operating systems, shells and applications as files are downloaded, opened, extracted, synchronized or deleted.

They can reveal URLs, referrers, timestamps, previous paths and container membership. Availability depends on what evidence still exists on the system.

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

Check what is available on the current machine or profile:

```bash
filegrail doctor
```

For another user profile or mounted copy:

```bash
filegrail doctor --home /mnt/profile
filegrail /mnt/evidence --home /mnt/profile
```

---

## Supported formats

### Embedded metadata

Metadata stored **inside the file** can reveal devices, GPS coordinates, timestamps, authors, editors, software, document properties, media tags and authenticity data.

Original field names are preserved in the report.

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

XMP, XMP history and IPTC can occur across multiple formats and are extracted wherever supported.

| Block | Typical data |
|:---|:---|
| **XMP** | Creating application, author, title, document IDs and derivation information |
| **XMP history** | Recorded editing steps and timestamps |
| **IPTC** | By-line, credit, source, copyright, headline, caption, keywords, place and creation date |

### Email

Saved email messages can expose their delivery path through `Received:` headers. With `--content`, readable `text/plain` and `text/html` message bodies are also inspected.

| Extension | Data extracted |
|:---|:---|
| `.eml` | Every `Received:` hop, connecting addresses and message headers |
| `.msg` | Transport headers where present, plus OLE document properties |

### Archives

`filegrail` can inspect supported files **inside archives without unpacking the archive into the scanned directory**.

Archive membership can also link an extracted file back to an entry by name and uncompressed size and, when available, inherit provenance from the archive itself.

| Extensions | What is read |
|:---|:---|
| `.zip` `.jar` `.whl` | Member names, sizes and metadata from supported files inside the archive |
| `.tar` `.tgz` `.gz` `.bz2` `.xz` | Members and supported metadata through the archive/compression layer |

### Torrents and sidecars

Torrent membership is matched when both **file name and exact size** agree with an entry.

A matching `<name>.info.json` can recover provenance for media downloaded with `yt-dlp`.

| File | Data extracted |
|:---|:---|
| `.torrent` | Trackers, creating client, comment, torrent membership and magnet/info-hash data |
| `<name>.info.json` | `yt-dlp` page URL, uploader/channel, publication date, extractor and fetch time |

### Document content

`--content` also scans the **text stored inside supported documents**.

The text itself is not added to the report. Only supported identifiers and their locations are retained.

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

The same identifier detection is applied to metadata and, with `--content`, document text. Filters remove common false positives.

| Type | Taken | Not taken |
|:---|:---|:---|
| `url` | `http` and `https` addresses, normalized | |
| `domain` | every host behind a URL or an address, and bare names whose TLD is a real one | anything shaped like a file name |
| `email` | addresses whose TLD is a real one | the address inside a message id - its host is still kept |
| `ipv4` | dotted quads, with private and reserved ranges marked as such | version numbers, and digits in a field naming software |
| `geo` | coordinates written with a hemisphere letter, a degree sign, a `geo:` URI, a map URL or an explicit latitude label | a bare pair of decimals, however many places it carries |
| `md5` `sha1` `sha256` | 32, 40 and 64 hex digits | digests in a field naming software, which are build ids |

Every value keeps its file, source and exact field or document location.

For the complete format reference and edge cases, see [`docs/FORMATS.md`](docs/FORMATS.md).

---

## Analysis

### Correlation and conflicts

When multiple sources describe the same file, `filegrail` compares them rather than choosing one automatically.

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

Every evidence record includes the basis of its association with the file. An exact recorded path and a filename-only match are therefore never presented as equivalent.

These values appear in the report's `match` column and under `match.method` in JSON.

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

`filegrail` does not assign evidence confidence scores. Instead it reports the category, source and match basis directly.

### Extracting investigation pivots from metadata and content

```bash
filegrail ./case --identify      # out of metadata
filegrail ./case --content       # out of metadata and document text
```

`--identify` extracts [supported identifier types](#identifier-types) from metadata and provenance records.

`--content` extends the same extraction to [supported document bodies](#document-content) and automatically enables identifier detection.

Results are grouped by type and retain the file, source and exact field or location. Values found across independent sources are highlighted separately.

### Clusters

```bash
filegrail ./photos --cluster
```

Groups files by shared identifying values and reports the field behind each grouping:

- **camera serial** - `EXIF · BodySerialNumber`: identifies the same physical camera.
- **camera model** - `EXIF · Make + Model`: identifies the same model, not the same device.
- **author** - `OOXML · creator` or equivalent: a recorded author value.

### Timeline

```bash
filegrail ./case --timeline
```

Combines available origin, metadata and activity timestamps into one chronological view.

### File relationships

XMP identifiers such as:

- `xmpMM:DocumentID`
- `xmpMM:InstanceID`
- `xmpMM:OriginalDocumentID`
- `xmpMM:DerivedFrom`

can link files even after renaming or export. Relationships can include derived-from, source-of, same-document and common-ancestor.

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

Running `filegrail` with no arguments displays the command overview without starting a scan.

### Commands

`filegrail PATH` is the normal scan form. `filegrail scan PATH` is its explicit equivalent.

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

A normal scan checks embedded metadata and available local provenance traces. Content inspection, hashing and clustering run only when requested.

`--home` uses another user profile, copied profile or mounted image as the source of local evidence.

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

Use `--out DIR` to write cleaned copies. Use `--check` to inspect what would be removed without writing anything.

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

After cleaning, each copy is scanned again. Any supported metadata that remains is reported.

Metadata removal is **not anonymization**. Pixels, sensor patterns, codec fingerprints and document content may still identify a source.

---

## JSON and automation

Use `--json` with scripts, `jq`, notebooks, pipelines or other tools. All main commands support machine-readable output with command-specific schemas and exit codes.

Schemas are versioned independently, so unrelated command changes do not force consumers to update.

| Schema | Since | What changed |
|:---|:---|:---|
| `filegrail.scan/2` | 0.8.0 | `files[].origins` became `files[].evidence`; every record carries `category` and `match`; `confidence` is gone; `reconciliation` is `correlation` |
| `filegrail.explain/2` | 0.8.0 | the same file document, and `conclusion` became `assessment` |
| `filegrail.compare/2` | 0.8.0 | `acquisition` became `origin` |
| `filegrail.doctor/1` | 0.3.0 | |
| `filegrail.clean/1` | 0.4.0 | |

Exit codes:

| Code | Meaning |
|:---|:---|
| `0` | The command ran. For `clean` and `clean --check`, every copy came out clean |
| `1` | `clean` only: metadata survived in at least one copy, or would |
| `2` | Invalid command input, such as a missing path, wrong argument count or unknown option |

A scan document contains `root`, `home`, `summary`, `files`, and when requested, `identifiers`, `shared_attributes` and `unsearched`.

Each file includes `path`, `size`, `mtime`, `btime`, `sha256`, `links` and `evidence`. Evidence records contain their `category`, `source`, `match` and decoded fields. Correlation results are stored under `correlation`.

---

## Privacy

`filegrail` runs locally and makes **no network requests**. The main privacy risk is the report itself.

Reports may contain:

- private URLs
- credentials or tokens embedded in URLs/commands
- file-system paths
- email addresses
- IP addresses
- GPS coordinates

Redact sensitive values before sharing output:

```bash
filegrail ./case --redact
```

or:

```bash
filegrail ./case --redact --json
```

Always review a redacted report before publishing it.

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
