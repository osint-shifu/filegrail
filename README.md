<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/osint-shifu/filegrail/master/assets/filegrail-stacked-compact-dark.png">
  <img src="https://raw.githubusercontent.com/osint-shifu/filegrail/master/assets/filegrail-stacked-compact-light.png" alt="filegrail" width="420">
</picture>

**Trace file origins. Extract metadata. Find investigative pivots.**

[![PyPI](https://img.shields.io/badge/pypi-v0.22.1-3775A9?style=flat-square)](https://pypi.org/project/filegrail/)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square)
![Runtime dependencies](https://img.shields.io/badge/runtime_dependencies-0-1f883d?style=flat-square)
![Local and read-only](https://img.shields.io/badge/local_%26_read--only-yes-1f883d?style=flat-square)
[![CI](https://github.com/osint-shifu/filegrail/actions/workflows/ci.yml/badge.svg)](https://github.com/osint-shifu/filegrail/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-Apache--2.0-8250df?style=flat-square)

[Features](#features) · [Quick start](#quick-start) · [Evidence](#evidence-sources) · [Formats](#supported-formats) · [Pivots](#investigative-pivots) · [Analysis](#analysis) · [Usage](#usage) · [Automation](#automation)

</div>

---

`filegrail` is a local command-line tool for investigating files and directories.

It combines the traces that the operating system and applications leave about a file with the metadata embedded in the file itself. From them it shows where a file came from, what it reveals, what happened to it on this machine and which identifiers can be followed up in OSINT or DFIR work.

| Area | What it answers |
| --- | --- |
| **Origin** | Where did the file come from and how did it arrive? |
| **Metadata** | What does the file reveal about devices, software, authors, timestamps, GPS and document history? |
| **Activity** | Was the file opened, synchronized, moved or deleted on this machine? |
| **Investigative pivots** | Which URLs, domains, IPs, hashes, accounts and other identifiers can be followed up? |

Analysis is **local**, makes **no network requests** and has **zero runtime dependencies**.

Scanning never modifies the files it examines. `filegrail clean` writes cleaned copies to a separate directory, and `-o` writes a report to the file you name.

## Quick start

Requires Python 3.10+ on Linux, macOS or Windows.

```bash
pipx install filegrail
```

or:

```bash
uv tool install filegrail
```

Analyze a file:

```bash
filegrail suspicious.pdf
```

Analyze a directory recursively:

```bash
filegrail ./evidence
```

Extract investigative pivots from metadata and provenance:

```bash
filegrail ./evidence --pivots
```

Also inspect the text of supported documents, including PDF:

```bash
filegrail ./evidence --content
```

Create a self-contained HTML investigation report:

```bash
filegrail ./evidence --content --html > report.html
```

[View an example HTML report](https://osint-shifu.github.io/filegrail/example-report.html), built from an invented case.

---

## Features

| Capability | Result |
| --- | --- |
| **File provenance** | Download URLs, referrers, fetch commands, archive and torrent membership, and local origin records |
| **Metadata extraction** | EXIF, XMP, IPTC, C2PA, document properties, media tags, mail headers and more |
| **Activity reconstruction** | Recent-file records, Windows shortcuts, trash records, sync folders and filesystem timestamps |
| **Evidence correlation** | Agreements and conflicts between independent sources |
| **Investigative pivots** | Structured identifiers with their type, file, source and exact location |
| **Content inspection** | Pivots from the text of supported documents without copying the text into the report |
| **Timeline** | Origin, creation, modification and activity events in chronological order |
| **File relationships** | XMP document identifiers and derivation chains between related files |
| **Clustering** | Files grouped by shared camera serial, camera model or recorded author |
| **File comparison** | Metadata, provenance and timing differences between two files |
| **Extension check** | Files whose content is a different format than their extension claims |
| **Evidence coverage** | Which local evidence sources are available and how far back they reach (`doctor`) |
| **Metadata removal** | Cleaned copies of supported files, scanned again to verify the result |
| **JSON and HTML output** | Machine-readable results for every main command, or the whole case as one self-contained page |

Evidence is not reduced to a confidence score. Every record keeps its **source**, **category** and **match basis**, so an exact recorded path is never presented as equivalent to a filename-only match.

---

## Evidence sources

`filegrail` combines evidence stored inside the file with traces left elsewhere on the system.

### Provenance and activity

These records exist outside the analyzed file. Browsers, operating systems, shells and applications leave them when files are downloaded, opened, extracted, synchronized or deleted.

What can be found depends on what still exists on the examined system.

| Source | What `filegrail` reads |
| --- | --- |
| **Browser download history** | Download URL, referrer, time and recorded size from Chrome, Chromium, Brave, Edge, Vivaldi and Firefox profiles |
| **Windows `Zone.Identifier`** | `HostUrl`, `ReferrerUrl` and `ZoneId` |
| **macOS Where From** | Download URL and referrer stored in `kMDItemWhereFroms` |
| **macOS quarantine** | Download URL, referrer, downloading application and quarantine time |
| **Linux XDG attributes** | `user.xdg.origin.url` and `user.xdg.referrer.url` |
| **Shell history** | Fetch commands such as `curl`, `wget`, `yt-dlp`, `scp`, `rsync`, `git`, `gh` and `aws`; other commands naming a file are recorded as activity |
| **Archives** | Membership matched by file name and uncompressed size; extracted files can inherit the archive's origin |
| **Torrent files and client stores** | Trackers, creating client, comment, magnet link and membership; local qBittorrent, Transmission and Deluge stores |
| **`yt-dlp` sidecars** | Page URL, uploader and channel, publication date, extractor and fetch time from `.info.json` |
| **Recent documents** | Linux desktop recent-file records |
| **Windows Recent shortcuts** | `.lnk` records showing that a file was opened |
| **Sync folders** | Nextcloud, Dropbox, Syncthing and OneDrive folder and account context |
| **Trash records** | Previous path and deletion time from the freedesktop trash |
| **Filesystem timestamps** | Creation and modification times of the file itself |
| **Messenger file names** | WhatsApp and Telegram Desktop naming patterns, treated as weak evidence |

Check which evidence sources are available:

```bash
filegrail doctor
```

Analyze files against another user profile, a copied profile or a mounted evidence set:

```bash
filegrail doctor --home /mnt/profile
filegrail /mnt/evidence --home /mnt/profile
```

Without `--home`, these records are read from the profile of the user running `filegrail`. `--no-shell-history` leaves shell history out.

"No evidence found" covers only the sources that were available to search.

### Embedded metadata

Metadata stored inside a file can reveal devices, GPS coordinates, timestamps, authors, editors, software, document properties, media tags and authenticity data.

Original field names are kept in the report.

| Metadata block | Extensions | Data extracted |
| --- | --- | --- |
| **EXIF** | `.jpg` `.jpeg` `.jpe` `.tif` `.tiff` `.dng` `.nef` `.cr2` `.arw` `.orf` `.rw2` `.webp` `.heic` `.heif` `.avif` | Camera make/model, body serial, lens, software, capture time, GPS |
| **PNG text** | `.png` `.apng` | Software, creation time, author and other text stored in the image |
| **ISO BMFF** | `.mp4` `.m4v` `.mov` `.qt` `.3gp` `.m4a` `.heic` `.heif` `.avif` | Encoder or recording device, creation time and location |
| **Matroska** | `.mkv` `.mk3d` `.webm` `.mka` | Writing application, creation date and tags |
| **RIFF/BWF** | `.wav` `.wave` `.rmi` `.avi` | Info fields such as title and software, recorder information, coding history and ID3 tags where present |
| **Vorbis comments** | `.flac` `.ogg` `.oga` `.opus` `.spx` | Encoder and every tag |
| **ID3** | `.mp3` `.aac` `.tta` | Encoding software, artist, title, date and other tags |
| **PDF Info** | `.pdf` | Producer, creator, author, title, subject, keywords and dates |
| **OOXML properties** | `.docx` `.docm` `.dotx` `.xlsx` `.xlsm` `.xltx` `.pptx` `.pptm` | Application, author, last editor, company, template, revision count and editing time |
| **OLE properties** | `.doc` `.dot` `.xls` `.xlt` `.ppt` `.pot` `.pps` `.msg` | Application, author, last editor, title, creation time and company |
| **OpenDocument metadata** | `.odt` `.ods` `.odp` `.odg` `.odf` `.ott` `.otp` | Generating application, author, title, creation date and editing statistics |
| **EPUB package** | `.epub` | Generating application, author, title and date |
| **RTF metadata** | `.rtf` | Generating application |
| **SVG metadata** | `.svg` | Generating application and author |
| **Jupyter notebook** | `.ipynb` | Kernel, language version and author |
| **C2PA** | `.jpg` `.jpeg` `.png` | Producing application, creation data, digital source type such as a generative AI model, and whether the file still matches its manifest |

XMP, XMP history and IPTC are not tied to one format and are read wherever a supported file carries them.

| Block | Data extracted |
| --- | --- |
| **XMP** | Creating application, author, title, document IDs and derivation information |
| **XMP history** | Recorded editing steps and timestamps |
| **IPTC** | By-line, credit, source, copyright, headline, caption, keywords, place and creation date |

---

## Supported formats

| Family | Examples |
| --- | --- |
| **Images** | JPEG, PNG, TIFF, WebP, HEIC, HEIF, AVIF and RAW (DNG, NEF, CR2, ARW, ORF, RW2) |
| **Documents** | PDF, DOCX, XLSX, PPTX, legacy Office, OpenDocument, RTF, EPUB, Jupyter notebooks |
| **Media** | MP4, MOV, M4A, MKV, WebM, WAV, AVI, FLAC, OGG, Opus, MP3 |
| **Email** | EML, MSG |
| **Archives** | ZIP, JAR, WHL, TAR, TGZ, GZ, BZ2, XZ |
| **Text and data** | TXT, Markdown, JSON, YAML, TOML, CSV, HTML, XML, GPX, KML, KMZ, GeoJSON, vCard, iCalendar |
| **Investigation data** | GEXF, GraphML, XMind, FreeMind, JSON Canvas, Maltego MTGX |
| **Provenance records** | `.torrent` files and `yt-dlp` `.info.json` sidecars |

What is read differs by format: embedded metadata, archive members, provenance records or, with `--content`, document text. The metadata read from each image, media and document format is listed under [Embedded metadata](#embedded-metadata).

A file in any other format still takes part in provenance analysis when a browser, shell or other local record names it.

### Email

Saved email messages can expose their delivery path through `Received:` headers.

| Extension | Data extracted |
| --- | --- |
| `.eml` | Every `Received:` hop, connecting addresses and message headers |
| `.msg` | Transport headers where present, plus OLE document properties |

### Archives

`filegrail` inspects supported files inside archives without unpacking them.

| Extensions | What is read |
| --- | --- |
| `.zip` `.jar` `.whl` | Member names, sizes and metadata from supported files inside |
| `.tar` `.tgz` `.gz` `.bz2` `.xz` | The same for tar archives and compressed files |

### Document content

`--content` reads the text of supported documents and looks for investigative pivots in it.

The text itself is not added to the report, only the values found and where they were found.

At most 1 MB of text is read from one file, and at most 64 parts of one document, such as slides or chapters.

| Extensions | Content read | Location reported as |
| --- | --- | --- |
| `.txt` `.text` `.md` `.markdown` `.rst` `.log` | Text | `line 12` |
| `.json` `.ndjson` `.jsonl` `.ipynb` `.yaml` `.yml` `.toml` `.ini` `.cfg` `.conf` `.vcf` `.ics` `.canvas` | Text | `line 12` |
| `.csv` `.tsv` | Each cell | `row 4 · column 3` |
| `.html` `.htm` `.xhtml` `.xml` `.svg` `.graphml` | Visible text and links | `line 12` |
| `.gpx` `.kml` | Names, links, named points and the start and end of every track | `line 12`, `waypoint 3`, `track 1 start`, `placemark 2` |
| `.geojson` | Text, every point and the start and end of every line | `line 12`, `feature 1`, `feature 1 end` |
| `.gexf` `.mm` | Visible text, links and node labels | `line 12` |
| `.pdf` | The text of each page | `page 7` |
| `.docx` `.docm` `.dotx` | Body, footnotes, endnotes and comments | `body`, `footnotes`, `endnotes`, `comments` |
| `.xlsx` `.xlsm` `.xltx` | Cell text | `cell text`, `sheet 2` |
| `.pptx` `.pptm` | Slide text and notes | `slide 4`, `slide 4 notes` |
| `.odt` `.ods` `.odp` `.odg` `.odf` `.ott` `.otp` | Document body, headers and footers | `body`, `headers and footers` |
| `.epub` | Chapters | chapter file name |
| `.kmz` | Embedded KML names, links and positions | `map`, `placemark 2` |
| `.xmind` | Map topics | `body` |
| `.mtgx` | Entities and their values from every graph | `graph 1` |
| `.eml` `.msg` | Message body, every text part | `body`, `body (html)` |

A scanned PDF page is a picture of text, and no OCR is performed.

See [docs/FORMATS.md](docs/FORMATS.md) for the complete format reference, including the formats the extension check recognizes and the detection rules for every pivot type.

---

## Investigative pivots

```bash
filegrail ./case --pivots
```

extracts supported identifiers from metadata and provenance records.

```bash
filegrail ./case --content
```

also reads the text of supported documents and turns pivot extraction on.

Every pivot keeps its **type**, **normalized value**, **file**, **source** and **exact location**, such as a metadata field, a line, a page or a slide. Values found in more than one file are counted as shared pivots.

Supported pivot types, with the name each has in JSON:

- URLs, domains, hostnames and email addresses: `url`, `domain`, `hostname`, `email`
- message IDs: `message_id`
- IPv4 and IPv6 addresses: `ipv4`, `ipv6`
- cryptographic hashes: `md5`, `sha1`, `sha256`, `sha512`
- geographic coordinates: `geo`
- CVE, CWE and GHSA identifiers: `cve`, `cwe`, `ghsa`
- Windows paths, registry keys, SIDs and executable names: `path`, `registry`, `sid`, `executable`
- MAC addresses and autonomous system numbers: `mac`, `asn`
- Tor onion addresses: `onion`
- cryptocurrency addresses: `btc`, `bch`, `ltc`, `doge`, `xmr`, `eth`
- people, organizations and online accounts: `person`, `org`, `handle`
- postal codes: `postcode`
- vehicle identification numbers: `vin`
- IBAN, BIC/SWIFT and US routing numbers: `iban`, `bic`, `aba`
- VAT, NIP, REGON, EIN, UK company and SEC CIK numbers: `vat`, `nip`, `regon`, `ein`, `crn`, `cik`
- US Social Security numbers: `ssn`
- analytics and advertising tracker IDs: `tracker`
- API keys, tokens and private keys: `secret`

Filters remove common false positives such as software version numbers, file names that only look like domains and hexadecimal build identifiers.

A detected secret or US Social Security number is reported as its type and a fingerprint, never as the value.

---

## Analysis

### Timeline

```bash
filegrail ./case --timeline
```

Combines available origin, metadata and activity timestamps into one chronological view.

### Clusters

```bash
filegrail ./photos --cluster
```

Groups files by shared identifying values and names the field behind each group:

- **camera serial** (`EXIF · BodySerialNumber`): the same recorded physical camera;
- **camera model** (`EXIF · Make + Model`): the same model, not necessarily the same device;
- **author** (`OOXML · creator` or equivalent): the same recorded author value.

### File relationships

XMP identifiers such as `xmpMM:DocumentID`, `xmpMM:InstanceID`, `xmpMM:OriginalDocumentID` and `xmpMM:DerivedFrom` can link files after renaming or export. A relationship is reported as derived-from, source-of, same-document or common-ancestor.

### Explain

```bash
filegrail explain document.pdf
```

Shows the evidence behind the findings for one file.

### Compare

```bash
filegrail compare original.docx edited.docx
```

Compares metadata, provenance and timing between two files.

### Correlation and conflicts

When several sources describe the same file, `filegrail` compares them and keeps every value instead of silently choosing one. It reports:

- several sources supporting the same origin;
- conflicting origin URLs;
- file-size mismatches;
- filename-only matches;
- a file reporting that it was created after it arrived here;
- creation and modification dates in impossible order;
- XMP editing steps out of sequence;
- EXIF, IPTC or PDF Info fields that disagree with XMP;
- C2PA hard-binding mismatches.

Files whose content is a different format than their extension claims are listed together among the key findings. A format several extensions legitimately share, such as a ZIP under `.docx`, `.epub` or `.jar`, is not reported.

Correlation is evidence for investigation, not automatic attribution.

### Match basis

Every evidence record states how it was associated with the file. These values appear in the report's `match` column and under `match.method` in JSON.

| Basis | What it means | Where it comes from |
| --- | --- | --- |
| `embedded` | Decoded from the file's own bytes | EXIF, XMP, IPTC, document properties, Content Credentials, mail headers |
| `file-attribute` | Read from what the filesystem keeps for this exact file | `Zone.Identifier`, macOS Where From, XDG attributes, creation times |
| `recorded-path` | An external store names this exact path | Browser download history, Recent Documents |
| `sidecar` | A separate file written next to it and naming it | `yt-dlp` sidecar, freedesktop trash record |
| `name+size` | Both name and size agree | Torrents, archive members, Windows shortcuts |
| `filename` | Only the name matched | A download record for a file that has since moved, a messenger naming pattern |
| `container-member` | Read from a member, or inherited from the container | Archives |
| `sync-root` | The file lies under a folder managed by a supported client | Nextcloud, Dropbox, Syncthing, OneDrive |

---

## Usage

```text
filegrail <path> [options]
filegrail <command> [options]
```

Running `filegrail` with no arguments shows the command overview without starting a scan.

A directory scan prints an investigation report: summary, key findings, a numbered file index, investigative pivots, the detail of files that need it, evidence coverage and conflicts. Files, findings, conflicts and pivots are numbered (`#001`, `F01`, `C01`, `P01`) and referenced across the report.

### Commands

| Command | Purpose |
| --- | --- |
| `filegrail PATH` | Analyze one file or directory |
| `filegrail scan PATH` | Explicit scan form |
| `filegrail explain FILE` | Show the evidence behind findings for one file |
| `filegrail compare A B` | Compare two files |
| `filegrail doctor` | Show available local evidence sources and coverage |
| `filegrail clean PATH --out DIR` | Write metadata-cleaned copies |
| `filegrail clean PATH --check` | Check cleaning without writing files |
| `filegrail menu` | Interactive command menu |
| `filegrail help COMMAND` | Command-specific help |

### Scan options

A normal scan reads embedded metadata and the available local provenance traces. Pivot extraction, content inspection, hashing and clustering run only when requested.

| Option | Purpose |
| --- | --- |
| `--brief` | Summary, key findings and a one-line file index |
| `-v`, `--verbose` | Every file in full detail, with every decoded field and the full pivot lists |
| `--pivots` | Extract investigative pivots from metadata and provenance |
| `--content` | Also read the text of supported documents; turns on `--pivots` |
| `--timeline` | Chronological event view |
| `--cluster` | Group files by shared cameras and authors |
| `--unknown-only` | Show only files with no evidence found |
| `--hash` | Compute SHA-256 for each file |
| `--type NAME` | Filter by `archive`, `audio`, `document`, `image`, `mail`, `text` or `video` |
| `--ext LIST` | Filter by extensions, e.g. `--ext jpg,pdf` |
| `--limit N` | Limit the list of files with no evidence found; `0` means all |
| `--home DIR` | Read evidence from another user profile |
| `--redact` | Redact credentials before printing |
| `-j`, `--json` | JSON output |
| `--html` | Self-contained HTML output |
| `-o`, `--out FILE` | Write the report to a file instead of standard output |
| `--no-recurse` | Do not scan subdirectories |
| `--no-skip` | Include normally skipped build, cache and vendor directories |
| `--no-shell-history` | Do not use shell history |
| `--no-archives` | Do not give an archive's origin to the files inside it |
| `--color`, `--no-color` | Force or disable ANSI color |

### Common tasks

| Task | Command |
| --- | --- |
| Find where a file came from | `filegrail download.pdf` |
| See the evidence behind a finding | `filegrail explain download.pdf` |
| Get an overview of a large directory | `filegrail ./case --brief` |
| List the identifiers in a set of documents | `filegrail ./case --content` |
| Find photos taken with the same camera | `filegrail ./photos --cluster` |
| Put everything that happened in order | `filegrail ./case --timeline` |
| Investigate a copied profile or mounted image | `filegrail /mnt/evidence --home /mnt/profile` |
| Export JSON with a SHA-256 for every file | `filegrail ./case --hash --json > report.json` |
| Share a report with credentials redacted | `filegrail ./case --content --redact --html -o report.html` |
| Check what would remain before publishing | `filegrail clean ./publish --check` |

---

## HTML reports

`--html` writes the same report as one self-contained page with:

- summary and key findings;
- a file index with filters;
- provenance and metadata evidence for every file;
- investigative pivots;
- evidence coverage and conflicts;
- tables that sort by any column;
- files, findings, conflicts and pivots linked to each other;
- a search box over the whole report;
- a dark and a light theme, and a light print layout.

The page loads nothing from outside itself and makes no network requests, so it opens offline and travels as a single file.

```bash
filegrail ./case --content --html -o report.html
```

[See an example report](https://osint-shifu.github.io/filegrail/example-report.html), built from an invented case.

---

## Metadata removal

`filegrail clean` removes supported metadata from copies. Original files are never modified.

### Cleanable formats

| Family | Extensions |
| --- | --- |
| **JPEG** | `.jpg` `.jpeg` `.jpe` |
| **PNG** | `.png` `.apng` |
| **ISO BMFF media** | `.mp4` `.m4v` `.m4a` `.mov` `.qt` `.3gp` |
| **Microsoft OOXML** | `.docx` `.docm` `.dotx` `.xlsx` `.xlsm` `.xltx` `.pptx` `.pptm` |
| **OpenDocument** | `.odt` `.ods` `.odp` `.odg` `.ott` `.otp` |

Clean one file or a directory:

```bash
filegrail clean ./publish --out ./clean
```

Check what would remain without writing files:

```bash
filegrail clean ./publish --check
```

| Option | Purpose |
| --- | --- |
| `--out DIR` | Output directory for cleaned copies; it cannot be inside the directory being cleaned |
| `--check` | Check cleaning without writing files |
| `--overwrite` | Replace an existing destination file |
| `--type NAME` | Filter by file family |
| `--ext LIST` | Filter by extension |
| `--no-recurse` | Do not descend into subdirectories |
| `-j`, `--json` | JSON output |

After cleaning, each copy is scanned again and any supported metadata that remains is reported.

Metadata removal is **not anonymization**. Pixels, sensor patterns, codec fingerprints, document content and other information outside supported metadata structures may still identify a source.

---

## Automation

Scans and the `explain`, `compare`, `doctor` and `clean` commands all have JSON output for `jq`, Python, notebooks and pipelines:

```bash
filegrail ./case --json > report.json
```

For example, with `jq`:

```bash
# The origin URL of every file that has one
filegrail ./case --json | jq -r '.files[] | .path as $file | .evidence[] | select(.category == "origin" and .url) | "\($file)\t\(.url)"'

# Every email address found in metadata and documents
filegrail ./case --content --json | jq -r '.identifiers[] | select(.type == "email") | .normalized'

# Pivots found in more than one file
filegrail ./case --content --json | jq -r '.identifiers[] | select(.files > 1) | "\(.type)\t\(.normalized)\t\(.files) files"'
```

Each command has its own schema version, which changes only when a field in that document changes meaning or is removed.

| Command | Schema |
| --- | --- |
| `scan` | `filegrail.scan/2` |
| `explain` | `filegrail.explain/2` |
| `compare` | `filegrail.compare/2` |
| `doctor` | `filegrail.doctor/1` |
| `clean` | `filegrail.clean/1` |

Every scan document contains `schema`, `filegrail_version`, `root`, `summary`, `files` and `unsearched`, and depending on how the scan was run also `home` (with `--home`), `identifiers` (with `--pivots` or `--content`) and `shared_attributes` (with `--cluster`).

Each file includes `path`, `size`, `mtime`, `btime`, `sha256`, `links` and `evidence`. Evidence records carry their `category`, `source`, `match` and decoded fields, and correlation results are stored under `correlation`.

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | The command ran successfully; for `clean` and `clean --check`, every copy came out clean |
| `1` | `clean` only: supported metadata remained, or would remain, in at least one copy |
| `2` | Invalid command input, such as a missing path, wrong argument count or unknown option |

---

## Privacy and limitations

`filegrail` runs locally and does not query external services.

The generated report is the main privacy risk. It can contain private URLs, credentials in URLs or commands, filesystem paths and account names, email addresses, names of people and organizations, IP addresses, machine names, hardware addresses, GPS coordinates, postal addresses, bank, tax and company identifiers, vehicle identification numbers, wallet addresses and tracker IDs.

`--redact` replaces credentials found in URLs and commands, such as tokens, API keys and passwords, with a fingerprint:

```bash
filegrail ./case --redact
```

Other values are not redacted, so review the output before sharing it.

`filegrail` analyzes evidence that still exists:

- cleared browser history, removed extended attributes or missing shell history cannot be reconstructed;
- a sync folder shows folder and account context, not who uploaded a file;
- messenger filename patterns do not identify a sender or conversation;
- an archive or torrent match by name and size is an association, not proof of authorship or intent;
- a shared camera model does not identify the same physical camera, while a body serial is a much stronger link;
- recorded author and organization metadata can be edited and is not a verified identity;
- C2PA hard binding is checked, but certificate chains and signature trust are **not** verified.

It is not a monitoring agent, a chain-of-custody system, a full disk-forensics suite, an automatic attribution engine or an OSINT enrichment service.

---

## Documentation

- [Format and detection reference](docs/FORMATS.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## License

Apache-2.0.
