<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/osint-shifu/filegrail/master/assets/filegrail-stacked-compact-dark.png">
  <img src="https://raw.githubusercontent.com/osint-shifu/filegrail/master/assets/filegrail-stacked-compact-light.png" alt="filegrail" width="420">
</picture>

**Trace file origins. Extract metadata. Find investigative pivots.**

[![PyPI](https://img.shields.io/badge/pypi-v0.23.0-3775A9?style=flat-square)](https://pypi.org/project/filegrail/)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square)
![Runtime dependencies](https://img.shields.io/badge/runtime_dependencies-0-1f883d?style=flat-square)
![Local and read-only](https://img.shields.io/badge/local_%26_read--only-yes-1f883d?style=flat-square)
[![CI](https://github.com/osint-shifu/filegrail/actions/workflows/ci.yml/badge.svg)](https://github.com/osint-shifu/filegrail/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-Apache--2.0-8250df?style=flat-square)

[Features](#features) · [Quick start](#quick-start) · [Evidence](#evidence-sources) · [Formats](#supported-formats) · [Pivots](#investigative-pivots) · [Analysis](#analysis) · [Usage](#usage) · [Automation](#automation)

</div>

---

`filegrail` reconstructs file provenance, extracts metadata, correlates evidence and finds investigative pivots across both metadata and file content.

It combines information stored inside files with traces left by browsers, operating systems, shells and other applications to show where a file came from, what happened to it on the machine and what can be followed further in OSINT or DFIR work.

| Area | What it answers |
| --- | --- |
| **Origin** | Where did the file come from and how did it reach this machine? |
| **Metadata** | What does it reveal about devices, software, authors, timestamps, GPS and document history? |
| **Activity** | Was it opened, synchronized, moved, extracted or deleted? |
| **Investigative pivots** | Which URLs, domains, IPs, hashes, accounts and other identifiers can be followed further? |

Analysis is **local**, makes **no network requests** and has **zero runtime dependencies**.

Scanning never modifies the files it examines. `filegrail clean` writes cleaned copies to a separate directory, and `-o` writes the report to the file you specify.

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

Extract investigative pivots from supported document content, including PDF:

```bash
filegrail ./evidence --pivots --content
```

Create a self-contained HTML report:

```bash
filegrail ./evidence --pivots --content --html > report.html
```

[View an example HTML report](https://osint-shifu.github.io/filegrail/example-report.html), built from an invented case.

---

## Features

| Capability | Result |
| --- | --- |
| **File provenance** | Download URLs, referrers, fetch commands, archive and torrent membership, and local origin records |
| **Metadata extraction** | EXIF, XMP, IPTC, C2PA, document properties, media tags, mail headers and more |
| **Activity reconstruction** | Recent-file records, Windows shortcuts, trash records, sync folders and filesystem timestamps |
| **Evidence correlation** | Matching and conflicting values across independent evidence sources |
| **Investigative pivots** | Structured identifiers with their type, file, source and exact location |
| **Content inspection** | Pivots extracted from supported document content |
| **Timeline** | Origin, creation, modification and activity events in chronological order |
| **File relationships** | XMP document identifiers and derivation chains between related files |
| **Clustering** | Files grouped by shared camera serial, camera model or recorded author |
| **File comparison** | Metadata, provenance and timing differences between two files |
| **Extension check** | Files whose actual content does not match their extension |
| **Evidence coverage** | Available local evidence sources and how far back they reach (`doctor`) |
| **Metadata removal** | Cleaned copies of supported files, scanned again to verify the result |
| **JSON and HTML output** | Machine-readable output for main commands, or the full case as one self-contained page |

Every finding shows where it came from and how it was matched to the file. Exact path matches are kept separate from weaker filename-only matches.

---

## Evidence sources

`filegrail` reads evidence from two places: data stored inside the file and traces stored elsewhere on the system.

### Provenance and activity

These records exist outside the analyzed file. Browsers, operating systems, shells and applications can leave them when files are downloaded, opened, extracted, synchronized or deleted.

What can be found depends on which records still exist on the examined system.

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

Without `--home`, these records are read from the profile of the user running `filegrail`. `--no-shell-history` excludes shell history.

"No evidence found" means no evidence was found in the sources that were available to search.

### Embedded metadata

Metadata stored inside a file can reveal devices, GPS coordinates, timestamps, authors, editors, software, document properties, media tags and authenticity data.

Original field names are kept in the report.

| Metadata block | Extensions | Data extracted |
| --- | --- | --- |
| **EXIF** | `.jpg` `.jpeg` `.jpe` `.tif` `.tiff` `.dng` `.nef` `.cr2` `.arw` `.orf` `.rw2` `.webp` `.heic` `.heif` `.avif` | Camera, lens, software, capture time and GPS; JPEG JFIF/JFXX and ICC profile metadata |
| **Photoshop resources** | `.jpg` `.jpeg` `.jpe` `.tif` `.tiff` `.psd` `.psb` | Resolution, JPEG settings, embedded-thumbnail descriptors, paths, workflow URLs and version information |
| **PNG text** | `.png` `.apng` | Software, creation time, author and other text stored in the image |
| **ISO BMFF** | `.mp4` `.m4v` `.mov` `.qt` `.3gp` `.m4a` `.heic` `.heif` `.avif` | Encoder or recording device, creation time and location |
| **Matroska** | `.mkv` `.mk3d` `.webm` `.mka` | Writing application, creation date and tags |
| **RIFF/BWF** | `.wav` `.wave` `.rmi` `.avi` | Info fields such as title and software, recorder information, coding history and ID3 tags where present |
| **Vorbis comments** | `.flac` `.ogg` `.oga` `.opus` `.spx` | Encoder and every tag |
| **ID3** | `.mp3` `.aac` `.tta` | Encoding software, artist, title, date and other tags |
| **PDF Info** | `.pdf` | Producer, creator, author, title, subject, keywords and dates |
| **OOXML properties** | `.docx` `.docm` `.dotx` `.xlsx` `.xlsm` `.xltx` `.pptx` `.pptm` | Application, author, last editor, company, template, revision count and editing time |
| **OLE properties** | `.doc` `.dot` `.xls` `.xlt` `.ppt` `.pot` `.pps` `.msg` | Summary properties, storage metadata, orphaned entries, VBA/XLM indicators and embedded-object paths |
| **OpenDocument metadata** | `.odt` `.ods` `.odp` `.odg` `.odf` `.ott` `.otp` | Generating application, author, title, creation date and editing statistics |
| **EPUB package** | `.epub` | Generating application, author, title and date |
| **RTF metadata** | `.rtf` | Generating application |
| **SVG metadata** | `.svg` | Generating application and author |
| **Jupyter notebook** | `.ipynb` | Kernel, language version and author |
| **Web document** | `.html` `.htm` `.xhtml` | Author, publisher, generator, dates, canonical URL, Open Graph, Twitter Cards and JSON-LD |
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

What `filegrail` reads depends on the format: embedded metadata, archive members, provenance records or, with `--content`, document content. Metadata coverage for image, media and document formats is listed under [Embedded metadata](#embedded-metadata).

Other file formats can still be matched against browser, shell and other local records.

### Email

Saved email messages can reveal their delivery path through `Received:` headers.

| Extension | Data extracted |
| --- | --- |
| `.eml` | Every `Received:` hop, connecting addresses and message headers |
| `.msg` | Transport headers where present, plus OLE metadata |

### Archives

`filegrail` reads supported files inside archives without unpacking them.

| Extensions | What is read |
| --- | --- |
| `.zip` `.jar` `.whl` | Member names, sizes and metadata from supported files inside |
| `.tar` `.tgz` `.gz` `.bz2` `.xz` | The same for tar archives and compressed files |

### Document content

`--content` reads supported document content and extracts investigative pivots from it.

The source text itself is not added to the report. Only detected values and their locations are reported.

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

Scanned PDF pages contain images of text. `filegrail` does not perform OCR.

See [docs/FORMATS.md](docs/FORMATS.md) for the complete format reference, including formats recognized by the extension check and detection rules for every pivot type.

---

## Investigative pivots

```bash
filegrail ./case --pivots
```

Extracts supported identifiers from metadata and provenance.

```bash
filegrail ./case --pivots --content
```

Also extracts them from supported document content.

Every pivot includes its **type**, **normalized value**, **file**, **source** and **exact location**, such as a metadata field, line, page or slide. Values found in more than one file are counted as shared pivots.

Supported pivot types, with their JSON names:

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

Detected secrets and US Social Security numbers are reported as a type and fingerprint, never as the raw value.

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

Groups files by shared identifying values:

- **camera serial** (`EXIF · BodySerialNumber`): the same recorded physical camera;
- **camera model** (`EXIF · Make + Model`): the same model, not necessarily the same device;
- **author** (`OOXML · creator` or equivalent): the same recorded author value.

### File relationships

XMP identifiers such as `xmpMM:DocumentID`, `xmpMM:InstanceID`, `xmpMM:OriginalDocumentID` and `xmpMM:DerivedFrom` can link files after renaming or export. Relationships are reported as derived-from, source-of, same-document or common-ancestor.

The self-contained HTML report includes an evidence-backed relationship explorer for files, identifiers, people and devices.

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

When several sources describe the same file, `filegrail` compares them and keeps conflicting values instead of choosing one automatically. It reports:

- several sources supporting the same origin;
- conflicting origin URLs;
- file-size mismatches;
- filename-only matches;
- a file reporting that it was created after it arrived on the machine;
- creation and modification dates in impossible order;
- XMP editing steps out of sequence;
- EXIF, IPTC or PDF Info fields that disagree with XMP;
- C2PA hard-binding mismatches.

Files whose actual content does not match their extension are listed among the key findings. Formats that legitimately use another container format, such as ZIP-based `.docx`, `.epub` or `.jar` files, are not reported as mismatches.

Correlation helps identify evidence worth investigating. It does not perform automatic attribution.

### Match basis

Every evidence record shows how it was matched to the file.

| Basis | What it means | Where it comes from |
| --- | --- | --- |
| `embedded` | Read from the file itself | EXIF, XMP, IPTC, document properties, Content Credentials, mail headers |
| `file-attribute` | Stored by the filesystem for this exact file | `Zone.Identifier`, macOS Where From, XDG attributes, creation times |
| `recorded-path` | An external record contains the exact path | Browser download history, Recent Documents |
| `sidecar` | A separate file stored next to the file and linked by name | `yt-dlp` sidecar, freedesktop trash record |
| `name+size` | File name and size both match | Torrents, archive members, Windows shortcuts |
| `filename` | Only the file name matches | A download record for a file that has moved, a messenger naming pattern |
| `container-member` | Read from a container member or inherited from the container | Archives |
| `sync-root` | The file is inside a folder managed by a supported sync client | Nextcloud, Dropbox, Syncthing, OneDrive |

---

## Usage

```text
filegrail <path> [options]
filegrail <command> [options]
```

Running `filegrail` with no arguments shows the command overview without starting a scan.

A directory scan prints an investigation report with a summary, key findings, numbered file index, investigative pivots, file details, evidence coverage and conflicts. Files, findings, conflicts and pivots are numbered (`#001`, `F01`, `C01`, `P01`) and referenced across the report.

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

A normal scan reads embedded metadata and available local provenance records. Pivot extraction, content inspection, hashing and clustering run only when requested.

| Option | Purpose |
| --- | --- |
| `--brief` | Summary, key findings and a one-line file index |
| `-v`, `--verbose` | Every file in full detail, with every decoded field and the full pivot lists |
| `--pivots` | Extract investigative pivots from metadata and provenance |
| `--content` | Also extract pivots from supported document content; enables `--pivots` |
| `--timeline` | Show events in chronological order |
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
| `--graphml` | Evidence graph as GraphML; enables pivot extraction |
| `--graph-csv` | One evidence-backed graph relationship per CSV row; enables pivot extraction |
| `-o`, `--out FILE` | Write the report to a file instead of standard output |
| `--no-recurse` | Do not scan subdirectories |
| `--no-skip` | Include normally skipped build, cache and vendor directories |
| `--no-shell-history` | Do not use shell history |
| `--no-archives` | Do not give an archive's origin to files inside it |
| `--color`, `--no-color` | Force or disable ANSI color |

### Common tasks

| Task | Command |
| --- | --- |
| Find where a file came from | `filegrail download.pdf` |
| Show the evidence behind a finding | `filegrail explain download.pdf` |
| Get an overview of a large directory | `filegrail ./case --brief` |
| Extract identifiers from documents | `filegrail ./case --pivots --content` |
| Find photos linked to the same camera | `filegrail ./photos --cluster` |
| Build a chronological timeline | `filegrail ./case --timeline` |
| Investigate a copied profile or mounted image | `filegrail /mnt/evidence --home /mnt/profile` |
| Export JSON with SHA-256 for every file | `filegrail ./case --hash --json > report.json` |
| Export the investigation graph for Gephi, yEd or Cytoscape | `filegrail ./case --graphml -o graph.graphml` |
| Export graph relationships for Neo4j or a spreadsheet | `filegrail ./case --graph-csv -o relationships.csv` |
| Create a report with credentials redacted | `filegrail ./case --pivots --content --redact --html -o report.html` |
| Check what metadata would remain before publishing | `filegrail clean ./publish --check` |

---

## HTML reports

`--html` creates the same investigation report as one self-contained page with:

- summary and key findings;
- a file index with filters;
- provenance and metadata evidence for every file;
- investigative pivots;
- evidence coverage and conflicts;
- sortable tables;
- links between files, findings, conflicts and pivots;
- full-report search;
- dark and light themes, plus a light print layout.

The report loads nothing from outside itself and makes no network requests. It works offline and can be shared as a single file.

```bash
filegrail ./case --pivots --content --html -o report.html
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

Clean one file or directory:

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
| `--no-recurse` | Do not scan subdirectories |
| `-j`, `--json` | JSON output |

After cleaning, every copy is scanned again and any supported metadata that remains is reported.

Metadata removal is **not anonymization**. Pixels, sensor patterns, codec fingerprints, document content and other information outside supported metadata structures may still identify a source.

---

## Automation

Scans and the `explain`, `compare`, `doctor` and `clean` commands support JSON output for `jq`, Python, notebooks and pipelines:

```bash
filegrail ./case --json > report.json
```

For example, with `jq`:

```bash
# The origin URL of every file that has one
filegrail ./case --json | jq -r '.files[] | .path as $file | .evidence[] | select(.category == "origin" and .url) | "\($file)\t\(.url)"'

# Every email address found in metadata and documents
filegrail ./case --pivots --content --json | jq -r '.identifiers[] | select(.type == "email") | .normalized'

# Pivots found in more than one file
filegrail ./case --pivots --content --json | jq -r '.identifiers[] | select(.files > 1) | "\(.type)\t\(.normalized)\t\(.files) files"'
```

Each command has its own schema version. The version changes only when a field changes meaning or is removed.

| Command | Schema |
| --- | --- |
| `scan` | `filegrail.scan/2` |
| `explain` | `filegrail.explain/2` |
| `compare` | `filegrail.compare/2` |
| `doctor` | `filegrail.doctor/1` |
| `clean` | `filegrail.clean/1` |

Every scan document contains `schema`, `filegrail_version`, `root`, `summary`,
`files`, `run`, `coverage` and `unsearched`. `run` records the effective scan
options, profile and filters. `coverage` records which evidence stores were
searched, unavailable, partial or disabled, how many artifacts were readable,
and which filesystem paths were skipped or unreadable.

Depending on the scan, it can also contain `home` (with `--home`), `identifiers`
and an evidence-backed `graph` (with `--pivots`, `--content` or `--hash`), and
`shared_attributes` (with `--cluster`). The first graph relationship connects a
file to every normalized pivot it carries and keeps the source, exact place,
corpus and count behind that edge, plus category, match basis and time where the
underlying evidence has them. A matched archive or torrent member also adds a
graph automatically because its evidence records the container path explicitly.
Resolved XMP derivation links do the same and name the exact fields matched at
both ends.

GraphML stores `run` and `coverage` as graph attributes. Graph CSV repeats the
same JSON documents on each relationship row, so an imported edge keeps the
conditions under which it was produced.

Each file includes `path`, `size`, `mtime`, `btime`, `sha256`, `links` and `evidence`. Evidence records include their `category`, `source`, `match` and decoded fields. Correlation results are stored under `correlation`.

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | The command ran successfully; for `clean` and `clean --check`, every copy came out clean |
| `1` | `clean` only: supported metadata remained, or would remain, in at least one copy |
| `2` | Invalid command input, such as a missing path, wrong argument count or unknown option |

---

## Privacy and limitations

`filegrail` runs locally and does not query external services.

Reports can contain sensitive data, including private URLs, credentials in URLs or commands, filesystem paths, account names, email addresses, names of people and organizations, IP addresses, machine names, hardware addresses, GPS coordinates, postal addresses, bank, tax and company identifiers, vehicle identification numbers, wallet addresses and tracker IDs.

`--redact` replaces credentials found in URLs and commands, such as tokens, API keys and passwords, with a fingerprint:

```bash
filegrail ./case --redact
```

Other values are not redacted, so review the report before sharing it.

`filegrail` can only analyze evidence that still exists:

- cleared browser history, removed extended attributes or missing shell history cannot be reconstructed;
- a sync folder shows folder and account context, not who uploaded a file;
- messenger filename patterns do not identify a sender or conversation;
- an archive or torrent match by name and size is an association, not proof of authorship or intent;
- a shared camera model does not identify the same physical camera, while a body serial is a much stronger link;
- recorded author and organization metadata can be edited and does not prove identity;
- C2PA hard binding is checked, but certificate chains and signature trust are **not** verified.

It is not a monitoring agent, chain-of-custody system, full disk-forensics suite, automatic attribution engine or OSINT enrichment service.

---

## Documentation

- [Format and detection reference](docs/FORMATS.md)
- [Changelog](CHANGELOG.md)
- [Roadmap](ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## License

Apache-2.0.
