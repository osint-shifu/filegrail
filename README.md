<div align="center">

# filegrail

**Local file provenance, metadata and forensic context analysis.**

Trace origins. Reveal metadata. Correlate evidence.

[![PyPI](https://img.shields.io/pypi/v/filegrail?style=flat-square&color=3775A9)](https://pypi.org/project/filegrail/)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square)
![68 formats](https://img.shields.io/badge/formats-68-8250df?style=flat-square)
![Runtime dependencies](https://img.shields.io/badge/runtime_dependencies-0-1f883d?style=flat-square)
![Local and read-only](https://img.shields.io/badge/local_%26_read--only-yes-1f883d?style=flat-square)
[![CI](https://github.com/osint-shifu/filegrail/actions/workflows/ci.yml/badge.svg)](https://github.com/osint-shifu/filegrail/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-Apache--2.0-8250df?style=flat-square)

[What it does](#what-it-does) · [Evidence sources](#evidence-sources) · [Supported formats](#supported-formats) · [Investigative pivots](#investigative-pivots) · [Analysis](#analysis) · [Installation](#installation) · [Usage](#usage) · [Examples](#examples)

</div>

---

`filegrail` helps determine where a file came from, what it records about itself, what happened to it locally, and which investigative pivots it exposes.

It correlates three categories of evidence:

| Category | Question | Examples |
| --- | --- | --- |
| **Origin** | How or from where did the file reach this environment? | Browser download history, `Zone.Identifier`, macOS Where From, XDG attributes, fetch commands, archives, torrents, `yt-dlp` sidecars |
| **Metadata** | What does the file record about itself? | EXIF, XMP, IPTC, document properties, media tags, email headers, Content Credentials |
| **Activity** | What happened to the file locally? | Recent-file records, Windows shortcuts, trash records, sync folders, filesystem timestamps |

With `--content`, supported document bodies can also be inspected for investigative pivots.

The document text itself is not printed or stored in the report. Only supported values and the locations where they were found are retained.

Every evidence record also states **how it was associated with the file** — for example by an exact recorded path, a file attribute, matching name and size, archive membership, filename-only association or the file's own bytes.

An exact recorded path and a weak filename-only match are therefore never presented as equivalent.

Scanning is local, read-only and makes no network requests.

`filegrail clean` is the only command that writes files. It creates cleaned copies in a separate destination and never modifies the originals.

---

## What it does

Give `filegrail` a file, directory, copied user profile or mounted evidence set and it examines the provenance traces and embedded metadata that apply.

Every result keeps its source visible.

When independent sources disagree, both values are preserved and the conflict is reported rather than silently resolved.

| Capability | What you get |
| --- | --- |
| **File provenance** | Where and how a file arrived, when it appeared and which source recorded it |
| **Metadata extraction** | Device, software, author, timestamps, GPS, revision data and other embedded fields |
| **Activity reconstruction** | Evidence that a file was opened, synchronized, moved, deleted or otherwise handled locally |
| **Evidence correlation** | Agreements and conflicts between independent sources |
| **Investigative pivots** | Supported pivot types with their file, source and exact location |
| **Content inspection** | Investigative pivots extracted from supported document bodies without copying the document text into the report |
| **Timeline** | Origin, creation, editing and activity events in chronological order |
| **File relationships** | XMP document identifiers and derivation chains between related files |
| **Clusters** | Files grouped by shared camera serial, camera model or recorded author |
| **Comparison** | Metadata, provenance and timing differences between two files |
| **Explanation** | Evidence behind findings for one file |
| **Metadata removal** | Cleaned copies of supported files with post-clean verification |
| **JSON output** | Machine-readable results for scans and all main commands |
| **Evidence coverage** | `doctor` shows which local evidence sources are available and, where possible, their coverage |

### Questions `filegrail` can help investigate

| Question | Relevant evidence |
| --- | --- |
| Where did this file come from? | Browser history, origin attributes, quarantine records, shell history, archives, torrents and sidecars |
| Which application downloaded or created it? | Browser records, quarantine data, embedded software/generator fields and document properties |
| Which device produced it? | EXIF camera model, body serial, lens and other device metadata |
| Where was it created or captured? | GPS metadata, geo pivots and recorded location fields |
| Who does the file identify as its author or organization? | Document properties, IPTC/XMP fields, mail headers and media tags |
| Was it opened or handled on this system? | Recent Documents, shortcuts, trash records, sync folders and filesystem timestamps |
| Do several sources support the same origin? | Evidence correlation |
| Do sources contradict one another? | Conflicting URLs, timestamps, file sizes and metadata fields |
| Are several files related? | XMP lineage, camera identifiers, authors and clustering |
| What can be used for further OSINT/DFIR enrichment? | URLs, domains, IPs, hashes, email addresses, CVEs, accounts, infrastructure identifiers, wallets and other investigative pivots |
| What happened first? | Combined timeline |
| Why was this finding produced? | `filegrail explain` |
| What evidence was actually available to search? | `filegrail doctor` |

---

## Evidence sources

### Origin and activity traces

These sources exist outside the analyzed file.

They are records left by browsers, operating systems, shells and applications as files are downloaded, opened, extracted, synchronized or deleted.

They can reveal URLs, referrers, timestamps, previous paths, downloading applications and container membership.

Availability depends on what evidence still exists on the system being examined.

| Source | What `filegrail` can read |
| --- | --- |
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

For another user profile, copied profile or mounted evidence source:

```bash
filegrail doctor --home /mnt/profile
filegrail /mnt/evidence --home /mnt/profile
```

A result of "no evidence found" should always be interpreted in the context of which evidence sources were actually available to search.

---

## Supported formats

### Embedded metadata

Metadata stored inside a file can reveal devices, GPS coordinates, timestamps, authors, editors, software, document properties, media tags and authenticity data.

Original field names are preserved in the report.

| Metadata block | Extensions | Data extracted |
| --- | --- | --- |
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
| --- | --- |
| **XMP** | Creating application, author, title, document IDs and derivation information |
| **XMP history** | Recorded editing steps and timestamps |
| **IPTC** | By-line, credit, source, copyright, headline, caption, keywords, place and creation date |

### Email

Saved email messages can expose their delivery path through `Received:` headers.

With `--content`, readable `text/plain` and `text/html` message bodies are also inspected for investigative pivots.

| Extension | Data extracted |
| --- | --- |
| `.eml` | Every `Received:` hop, connecting addresses and message headers |
| `.msg` | Transport headers where present, plus OLE document properties |

### Archives

`filegrail` can inspect supported files inside archives without unpacking the archive into the scanned directory.

Archive membership can also link an extracted file back to an entry by name and uncompressed size and, when available, inherit provenance from the archive itself.

| Extensions | What is read |
| --- | --- |
| `.zip` `.jar` `.whl` | Member names, sizes and metadata from supported files inside the archive |
| `.tar` `.tgz` `.gz` `.bz2` `.xz` | Members and supported metadata through the archive/compression layer |

### Torrents and sidecars

Torrent membership is matched when both file name and exact size agree with an entry.

A matching `<name>.info.json` can recover provenance for media downloaded with `yt-dlp`.

| File | Data extracted |
| --- | --- |
| `.torrent` | Trackers, creating client, comment, torrent membership and magnet/info-hash data |
| `<name>.info.json` | `yt-dlp` page URL, uploader/channel, publication date, extractor and fetch time |

### Document content

`--content` scans readable text stored inside supported documents for investigative pivots.

The text itself is not added to the report.

Only supported values and their locations are retained.

Content scanning is limited to 1 MB of text per file and 64 members of a packaged document.

| Extensions | Content read | Location reported as |
| --- | --- | --- |
| `.txt` `.text` `.md` `.markdown` `.rst` `.log` | Text by line | `line 12` |
| `.csv` `.tsv` `.json` `.ndjson` `.jsonl` `.ipynb` `.yaml` `.yml` `.toml` `.ini` `.cfg` `.conf` `.vcf` `.ics` `.canvas` | Text/data by line | `line 12` |
| `.html` `.htm` `.xhtml` `.xml` `.svg` `.graphml` | Visible text and relevant URLs/attributes | `line 12` |
| `.gpx` `.kml` | Names and links as markup, plus every named point and the start and end of every track as geo positions | `line 12`, `waypoint 3`, `track 1 start`, `placemark 2` |
| `.geojson` | Text by line, plus every point and the start and end of every line as geo positions | `line 12`, `feature 1`, `feature 1 end` |
| `.gexf` `.mm` | Visible text and links, plus node labels kept in attributes | `line 12` |
| `.docx` `.docm` `.dotx` | Body, footnotes, endnotes and comments | `body`, `footnotes`, `endnotes`, `comments` |
| `.xlsx` `.xlsm` `.xltx` | Shared strings and inline cell text | `cell text`, `sheet 2` |
| `.pptx` `.pptm` | Slide text and notes | `slide 4`, `slide 4 notes` |
| `.odt` `.ods` `.odp` `.odg` `.odf` `.ott` `.otp` | Document body, headers and footers | `body`, `headers and footers` |
| `.epub` | Chapters | chapter file name |
| `.kmz` | Embedded KML names, links and positions | `map`, `placemark 2` |
| `.xmind` | Topics from the JSON or XML body | `body` |
| `.mtgx` | Every graph of a Maltego export, including entities and their values | `graph 1` |
| `.eml` `.msg` | Decoded message body, every text part | `body`, `body (html)` |

PDF metadata is supported, but PDF body text is not extracted by `--content`.

---

## Investigative pivots

`filegrail` can detect **investigative pivots** (identifiers): structured values that may be useful for further OSINT, DFIR, threat-intelligence or attribution work.

```bash
filegrail ./case --identify
```

`--identify` extracts supported pivots from metadata and provenance records.

```bash
filegrail ./case --content
```

`--content` extends the same detection into supported document bodies and automatically enables pivot extraction.

Every result retains:

- the pivot type;
- its normalized value or safe representation;
- the file where it was found;
- the evidence source or document content;
- the exact metadata field, line, slide, sheet, chapter or other supported location.

Values found across independent sources can therefore be correlated instead of flattened into an untraceable list.

### Investigative pivot types

The same detection logic is applied to metadata and, with `--content`, document text.

Filters intentionally reject many ambiguous values to reduce false positives.

| Type | Taken | Not taken |
| --- | --- | --- |
| `url` | `http` and `https` addresses, normalized | |
| `domain` | Every host behind a URL or an address, and bare names whose TLD is a real one | Anything shaped like a file name, and onion names, which are their own type |
| `email` | Addresses whose TLD is a real one | The address inside a message ID; its host is still kept |
| `ipv4` | Dotted quads, with private and reserved ranges marked as such | Version numbers, and digits in a field naming software |
| `ipv6` | Addresses with all eight groups written out, or any form inside the brackets a URL places around one | A compressed address standing bare, which can resemble a scope operator in code |
| `geo` | Coordinates written with a hemisphere letter, a degree sign, a `geo:` URI, a map URL or an explicit latitude label | A bare pair of decimals |
| `md5` `sha1` `sha256` | 32, 40 and 64 hexadecimal digits, bare or as colon-separated pairs; a digest of an address seen in the same scan is named for it | Digests in a field naming software, which may be build IDs |
| `cve` | Vulnerability identifiers, case-insensitive | |
| `registry` | Windows Registry keys under any hive, long name or short, as one key | |
| `path` | Windows paths using a drive letter, environment variable or UNC share | POSIX paths; a bare drive or variable |
| `executable` | Bare names of Windows executables, scripts, installers or shortcuts, alone or inside a path or URL | Names with spaces, source files and anything ending in `com` |
| `btc` | Bitcoin addresses whose checksum holds, including legacy and `bc1`; Bech32 values are normalized to lowercase | Mixed-case `bc1` spelling |
| `eth` | Ethereum addresses, mixed-case ones validated using EIP-55 and one-case values by shape, normalized to lowercase | Transaction hashes |
| `vin` | Vehicle identification numbers when the North American check digit holds, and values beside a `VIN` label regardless | Other arbitrary seventeen-character strings |
| `iban` | Account numbers whose country, length and mod-97 check agree, with spaces removed | |
| `nip` `regon` | Polish tax and statistical numbers beside their label, or NIP behind an EU `PL` prefix | The same digits standing bare |
| `onion` | Tor v3 addresses whose checksum holds, normalized to lowercase | |
| `mac` | Hardware addresses in supported notations, normalized with colons | All-zero and broadcast addresses |
| `sid` | Windows account and group SIDs such as `S-1-5-21-…` with a relative ID | Short well-known SIDs such as `S-1-5-18` |
| `bic` | Bank identifier codes beside a `BIC` or `SWIFT` label, 8 or 11 characters, with a valid country code | The same code standing bare |
| `secret` | Vendor-prefixed API keys and tokens, JWTs and private-key blocks; reported as type and fingerprint, never as the secret value | Credentials detected only because of a nearby field name |
| `person` | Names in fields identifying who made a file — author, by-line, artist or mail display name — and names in text when preceded by supported honorifics | Arbitrary names in document text and common application placeholders |
| `org` | Company or credit fields and names in text ending with supported legal forms such as `Sp. z o.o.`, `GmbH`, `Ltd`, `Inc` or `LLC` | Ambiguous `Source` fields |
| `handle` | Accounts referenced through known-platform profile URLs and user-directory logins from the originating machine | Platform-owned pages and common system directories |
| `postcode` | Polish postcode with town context and UK postcodes recognized by shape | Bare ambiguous postal-looking values and US ZIP codes |
| `ssn` | US Social Security numbers beside their label and matching valid issuance shape; represented as a fingerprint, never the number | Bare values and ranges that were never issued |
| `ein` | US Employer Identification Numbers beside their label and using an assigned prefix | The same digits standing bare |
| `aba` | US bank routing numbers beside their label whose checksum and prefix are valid | Bare nine-digit values |
| `crn` | UK company registration numbers beside a Companies House or company-number label | Bare ambiguous values |
| `cik` | SEC filer identifiers beside a `CIK` label, normalized regardless of zero padding | |
| `vat` | EU VAT identifiers beside a `VAT` label and using a recognized country | Polish VAT values, which are represented as `nip` |
| `asn` | Autonomous system numbers such as `ASN 3356` or `AS3356` | Ambiguous uses of `AS` in normal text |
| `tracker` | Analytics, tag-manager, advertising and affiliate identifiers recognized by prefix or provider context, including values found in loader and pixel URLs | Numbers without a known prefix or provider context |

For the complete format reference and edge cases, see [`docs/FORMATS.md`](docs/FORMATS.md).

---

## Analysis

### Correlation and conflicts

When multiple sources describe the same file, `filegrail` compares them rather than choosing one automatically.

It can report:

- multiple sources supporting the same origin;
- conflicting origin URLs;
- file-size mismatches;
- filename-only matches;
- creation and modification dates in impossible order;
- XMP editing steps out of sequence;
- EXIF vs XMP differences;
- PDF Info vs XMP differences;
- XMP derivation relationships between files;
- C2PA hard-binding mismatches.

This is evidence correlation, not automatic attribution.

### How a record was matched to a file

Every evidence record includes the basis of its association with the file.

An exact recorded path and a filename-only match are therefore never presented as equivalent.

These values appear in the report's `match` column and under `match.method` in JSON.

| Basis | What it means | Where it comes from |
| --- | --- | --- |
| `embedded` | Decoded from the file's own bytes | EXIF, XMP, IPTC, document properties, Content Credentials, mail headers |
| `file-attribute` | Read from what the filesystem keeps for this exact file | `Zone.Identifier`, macOS Where From, XDG attributes, creation times |
| `recorded-path` | An external store names this exact path | Browser download history, Recent Documents |
| `sidecar` | A separate file written next to it and naming it | `yt-dlp` sidecar, freedesktop trash record |
| `name+size` | Both name and size agree | Torrents, archive members, Windows shortcuts |
| `filename` | The name is all that matched | A download record for a file that has since moved, a messenger naming pattern |
| `container-member` | Read from a member, or inherited from the container | Archives |
| `sync-root` | The file lies under a folder managed by a supported client | Nextcloud, Dropbox, Syncthing, OneDrive |

`filegrail` does not assign evidence confidence scores.

Instead it exposes the evidence category, source and match basis directly so the investigator can judge the association.

### Extracting investigative pivots from metadata and content

```bash
filegrail ./case --identify      # metadata and provenance
filegrail ./case --content       # metadata, provenance and supported document text
```

`--identify` extracts supported investigative pivots from metadata and provenance records.

`--content` extends the same extraction into supported document bodies and automatically enables pivot detection.

Results are grouped by type and retain the file, source and exact field or document location.

Values found across independent sources are highlighted separately.

### Timeline

```bash
filegrail ./case --timeline
```

Combines available origin, metadata and activity timestamps into one chronological view.

### Clusters

```bash
filegrail ./photos --cluster
```

Groups files by shared identifying values and reports the field responsible for each grouping.

Examples:

- **camera serial** — `EXIF · BodySerialNumber`: indicates the same recorded physical camera identifier;
- **camera model** — `EXIF · Make + Model`: identifies the same model, not necessarily the same physical device;
- **author** — `OOXML · creator` or equivalent: groups files carrying the same recorded author value.

### File relationships

XMP identifiers such as:

- `xmpMM:DocumentID`
- `xmpMM:InstanceID`
- `xmpMM:OriginalDocumentID`
- `xmpMM:DerivedFrom`

can link files even after renaming or export.

Relationships can include:

- derived-from;
- source-of;
- same-document;
- common-ancestor.

---

## Installation

Requires Python 3.10+.

Recommended:

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

`filegrail PATH` is the normal scan form.

`filegrail scan PATH` is its explicit equivalent.

| Command | Purpose |
| --- | --- |
| `filegrail PATH` | Scan one file or directory |
| `filegrail scan PATH` | Explicit scan command |
| `filegrail explain FILE` | Show the evidence behind findings for one file |
| `filegrail compare A B` | Compare two files |
| `filegrail doctor` | Show available local evidence sources and coverage |
| `filegrail clean PATH --out DIR` | Write metadata-cleaned copies |
| `filegrail clean PATH --check` | Check what cleaning would remove without writing files |
| `filegrail menu` | Interactive command menu |
| `filegrail help COMMAND` | Command-specific help |

### Scan options

A normal scan checks embedded metadata and available local provenance traces.

Investigative-pivot extraction, content inspection, hashing and clustering run only when requested.

`--home` uses another user profile, copied profile or mounted evidence source as the source of local evidence.

| Option | Purpose |
| --- | --- |
| `-v`, `--verbose` | Show every evidence record |
| `--brief` | Index only, without per-file detail |
| `--timeline` | Chronological event view |
| `--identify` | Extract investigative pivots from metadata and provenance |
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

Use `--out DIR` to write cleaned copies.

Use `--check` to inspect what would be removed without writing anything.

The output directory cannot be inside the directory being cleaned.

| Option | Purpose |
| --- | --- |
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

# Extract investigative pivots from metadata and provenance
filegrail ./case --identify

# Also inspect supported document content
filegrail ./case --content

# Build a timeline
filegrail ./case --timeline

# Find files sharing cameras or authors
filegrail ./case --cluster

# Explain exactly why a finding was produced
filegrail explain document.pdf

# Compare two files
filegrail compare original.docx edited.docx

# Analyze evidence using another user profile
filegrail /mnt/evidence --home /mnt/profile

# JSON report
filegrail ./case --json > report.json

# JSON report with credentials redacted
filegrail ./case --redact --json > report.json
```

---

## Metadata removal

`filegrail clean` removes supported metadata from copies.

Originals are never modified.

### Cleanable formats

| Family | Extensions |
| --- | --- |
| **JPEG** | `.jpg` `.jpeg` `.jpe` |
| **PNG** | `.png` `.apng` |
| **ISO BMFF media** | `.mp4` `.m4v` `.m4a` `.mov` `.qt` `.3gp` |
| **Microsoft OOXML** | `.docx` `.docm` `.dotx` `.xlsx` `.xlsm` `.xltx` `.pptx` `.pptm` |
| **OpenDocument** | `.odt` `.ods` `.odp` `.odg` `.ott` `.otp` |

Clean one file:

```bash
filegrail clean photo.jpg --out ./clean
```

Check without writing:

```bash
filegrail clean ./publish --check
```

After cleaning, each copy is scanned again.

Any supported metadata that remains is reported.

Metadata removal is **not anonymization**.

Pixels, sensor patterns, codec fingerprints, document content and other information outside supported metadata structures may still identify a source.

---

## JSON and automation

Use `--json` with scripts, `jq`, notebooks, pipelines or other tools.

All main commands support machine-readable output with command-specific schemas and exit codes.

Schemas are versioned independently so unrelated command changes do not force downstream consumers to update.

| Schema | Since | What changed |
| --- | --- | --- |
| `filegrail.scan/2` | 0.8.0 | `files[].origins` became `files[].evidence`; every record carries `category` and `match`; `confidence` was removed; `reconciliation` became `correlation` |
| `filegrail.explain/2` | 0.8.0 | Uses the same file document; `conclusion` became `assessment` |
| `filegrail.compare/2` | 0.8.0 | `acquisition` became `origin` |
| `filegrail.doctor/1` | 0.3.0 | |
| `filegrail.clean/1` | 0.4.0 | |

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | The command ran successfully. For `clean` and `clean --check`, every copy came out clean |
| `1` | `clean` only: metadata survived in at least one copy, or would survive |
| `2` | Invalid command input, such as a missing path, wrong argument count or unknown option |

A scan document contains:

- `root`
- `home`
- `summary`
- `files`

and, when requested:

- `identifiers`
- `shared_attributes`
- `unsearched`

Each file includes:

- `path`
- `size`
- `mtime`
- `btime`
- `sha256`
- `links`
- `evidence`

Evidence records contain their:

- `category`
- `source`
- `match`
- decoded fields

Correlation results are stored under `correlation`.

---

## Privacy

`filegrail` runs locally and makes no network requests.

The primary privacy risk is therefore usually **the generated report**, not the analysis itself.

Reports may contain:

- private URLs;
- credentials or tokens embedded in URLs or commands;
- filesystem paths and account names contained in them;
- email addresses;
- names of people and organizations recorded in files;
- IP addresses;
- hardware addresses;
- GPS coordinates;
- postal addresses;
- bank-account identifiers;
- tax identifiers;
- vehicle identification numbers;
- company registration numbers;
- cryptocurrency wallet addresses;
- analytics and advertising identifiers.

A supported credential found inside a document, and a US Social Security number, are reported as their kind and a fingerprint, never as the value.

Redact credentials before sharing output:

```bash
filegrail ./case --redact
```

or:

```bash
filegrail ./case --redact --json
```

Always review a redacted report before publishing or sharing it.

---

## Limits

`filegrail` reconstructs evidence that still exists.

It does not manufacture missing history.

- Cleared browser history, removed extended attributes or missing shell history cannot be reconstructed.
- A supported sync folder can show account/folder context, but not who uploaded a file.
- WhatsApp or Telegram filename patterns do not identify a sender or conversation and are treated as weak evidence.
- An archive member or torrent match based on name and size is an association, not proof of authorship or intent.
- A shared camera model does not identify the same physical camera; a body serial is a materially stronger link.
- Recorded author or organization metadata can be edited and should not be treated as verified identity by itself.
- C2PA hard binding is checked, but certificate-chain and signature trust are **not** verified.
- PDF metadata is read; PDF body text is not extracted by `--content`.
- Unsupported file formats can still participate in provenance analysis when external or local evidence about them exists.
- Negative findings depend on the evidence sources that were available to search.
- `filegrail` is not a monitoring agent.
- `filegrail` is not a chain-of-custody system.
- `filegrail` is not a full disk-forensics suite.
- `filegrail` does not perform network enrichment or automatically query external OSINT services.

---

## Documentation

- [Complete format reference](docs/FORMATS.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)

---

## License

Apache-2.0.
