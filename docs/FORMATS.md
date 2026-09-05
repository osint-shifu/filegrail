# Formats

What `filegrail` can read out of a file you point it at.

This is the reference list. The [README](../README.md) has the short version; this
one is complete, and it is checked against the code by
`tests/test_documented_formats.py` — a reader whose formats are missing here
fails a test, and so does a format listed here that nothing reads. It cannot
drift.

Two different questions get confused a lot, so to be clear about which one this
answers:

- **What the file says about itself** — EXIF, XMP, document properties, mail
  headers. That is this file.
- **What your machine remembers about the file** — browser history, OS origin
  attributes, quarantine records, shell history, Recent shortcuts. Different
  axis, and `filegrail doctor` tells you which of those are available.

---

## Metadata blocks

**68 file extensions** have a reader. Fifteen named metadata blocks, plus four
that turn up in any container that will carry them.

The first column is the `block` value you get in `--json`. It is what to filter
on when you want the PDFs rather than everything a file said about itself.

| Block | Extensions | What comes out |
|:---|:---|:---|
| `exif` | `.jpg` `.jpeg` `.jpe` `.tif` `.tiff` `.dng` `.nef` `.cr2` `.arw` `.orf` `.rw2` `.webp` `.heic` `.heif` `.avif` | Camera make and model, body serial, lens, software, capture time, GPS |
| `png-text` | `.png` `.apng` | `tEXt` / `zTXt` / `iTXt` keywords: software, creation time, author, and whatever a generator wrote there |
| `isobmff` | `.mp4` `.m4v` `.mov` `.qt` `.3gp` `.m4a` `.heic` `.heif` `.avif` | Encoder and recording device, creation time, ISO 6709 location |
| `matroska` | `.mkv` `.mk3d` `.webm` `.mka` | Writing application and library, segment date, tag entries |
| `riff` | `.wav` `.wave` `.rmi` `.avi` | `LIST`/`INFO` fields, BWF `bext` recorder and coding history, an `id3 ` chunk where one is present |
| `vorbis-comment` | `.flac` `.ogg` `.oga` `.opus` `.spx` | Vendor string and every `NAME=value` comment |
| `id3` | `.mp3` `.aac` `.tta` | ID3v2 frames: encoding software, artist, title, date |
| `pdf-info` | `.pdf` | The `Info` dictionary, through compressed object streams and hex strings |
| `ooxml-properties` | `.docx` `.docm` `.dotx` `.xlsx` `.xlsm` `.xltx` `.pptx` `.pptm` | `app.xml` and `core.xml`: application, author, last editor, company, template, revision count, total editing time |
| `ole-summary` | `.doc` `.dot` `.xls` `.xlt` `.ppt` `.pot` `.pps` `.msg` | `SummaryInformation` and `DocumentSummaryInformation` property sets |
| `odf-meta` | `.odt` `.ods` `.odp` `.odg` `.odf` `.ott` `.otp` | `meta.xml`: generator, author, creation and editing metadata |
| `epub-package` | `.epub` | OPF package metadata |
| `rtf-generator` | `.rtf` | The `\generator` and `\info` groups |
| `svg-metadata` | `.svg` | Generator, plus an embedded RDF block where an editor left one |
| `notebook-kernel` | `.ipynb` | Kernel name and language runtime version |
| `c2pa` | `.jpg` `.jpeg` `.png` | JUMBF manifest: producing application, creation data, digital source type |

Mail is not in this table because a message's metadata is its delivery record
rather than a block inside a container; it has a section of its own further
down. Neither are XMP and IPTC, which are not tied to an extension at all.

### Why so many fields

Because you rarely know in advance which one matters. A body serial ties images
to one camera. GPS time is often more trustworthy than the camera clock. Office
properties expose the last editor, the company, the template and how long
somebody had the document open.

So decoded fields stay visible by default. `--brief` folds them down, `--json`
keeps all of them, and long values wrap instead of being cut.

---

## Blocks with no format

Three readers do not care what the container is. They look for the block and
read it wherever it turns up.

| Block | Where it is found | What comes out |
|:---|:---|:---|
| `xmp` | Any file carrying an XMP packet — JPEG, TIFF and raw, PNG, PDF, MP4, HEIC, SVG, InDesign output, and containers nobody thought to list | Creating application, author, title, `xmpMM` derivation identifiers |
| `xmp-history` | The same packet | Every recorded editing step. A step with a timestamp becomes its own dated claim and lands on `--timeline`; one without stays a field, because inventing a time for it would be worse than leaving it undated |
| `iptc` | Any Photoshop image-resource block — JPEG, TIFF, PSD — plus TIFF tag 33723 | By-line, credit, source, copyright, headline, caption, keywords, place and date of creation |

XMP identifiers are also what links the scanned files to each other:
`xmpMM:DocumentID`, `OriginalDocumentID` and `DerivedFrom` let a master, its
export and a rendition of that export be reported as a chain. A shared
*original* is only ever reported as a common ancestor — a template carries its
XMP into everything made from it, and those files share an ancestor and nothing
else. The reasoning is in
[`docs/specs/2026-09-01-derivation-lineage.md`](specs/2026-09-01-derivation-lineage.md).

---

## Mail

A saved message is the one file type where the metadata *is* the provenance.
`Received:` headers are the only part of an email the sender did not write.

| Extension | What comes out |
|:---|:---|
| `.eml` | Every `Received:` hop as its own claim, the connecting address each server saw, and the sender's own headers kept separate from them |
| `.msg` | The same header block, out of the `PR_TRANSPORT_MESSAGE_HEADERS` MAPI stream. Where an Exchange delivery never wrote internet headers, the message's own MAPI properties are reported and no delivery record is invented |

The hops are not ranked alike. The topmost was written by the recipient's own
server and is the one hop nobody else could have forged; everything below it
was written by a machine the sender may control.

A `.msg` also goes through the `ole-summary` reader, because it is a compound
document and its Office-style properties sit exactly where a `.doc`'s do.

---

## Archives

Not metadata. These are read so that a file extracted from one can inherit the
archive's origin, when the member name and uncompressed size both match.

| Extensions | What filegrail does with them |
|:---|:---|
| `.zip` `.jar` `.whl` | Member names and uncompressed sizes |
| `.tar` `.tgz` `.gz` `.bz2` `.xz` | The same, through the compression |

The archive is considered whether or not it is inside the scanned tree — a case
directory is usually the *result* of unpacking something that lives elsewhere.

---

## Written from the specification

Three readers have never been run against a file the originating software
produced, because nothing on the developer's machine writes one. They are built
to the specification and tested against fixtures assembled from it, with every
offset computed rather than counted by hand.

| Reader | Specification | Why it is untested against reality |
|:---|:---|:---|
| Outlook `.msg` transport headers | [MS-OXMSG] | No Outlook here. The container walk underneath is not in this position — real `.doc` files exercise it |
| Windows `.lnk` shortcuts | [MS-SHLLINK] | No Windows desktop writing Recent entries |
| The `id3 ` chunk inside a WAV | ID3v2 in RIFF | Nothing available writes one; the rest of the RIFF reader is exercised by real files |

That is worth knowing before you rely on one of them in something that matters.

---

## Deliberately not read

| What | Why |
|:---|:---|
| Vendor maker notes | Every manufacturer encodes them differently and each needs its own parser. The rest of EXIF is decoded |
| C2PA signatures | Manifests are parsed; the certificate chain is **not** verified. A manifest says what it says, and this does not tell you whether to believe it |
| `.mbox` | Many messages, one record per file. There is no honest single claim to make about a mailbox |
| Jump Lists (`.automaticDestinations-ms`) | In the Recent folder beside the shortcuts, and a different format. Shortcuts first |
| Fixed-length MAPI properties | Delivery and submit times live in `__properties_version1.0`, not a `__substg1.0_` stream. Left unread rather than guessed at, with no real `.msg` to check the layout against |
| PNG `Creation Time` in RFC 1123 form | Skipped rather than compared against XMP, because parsing it touches the moment path shared with EXIF, IIM and PDF |

Anything else is still scanned. A format `filegrail` does not understand is
reported as not understood, rather than guessed at.

---

## Filtering by any of this

```bash
filegrail . --type image          # image, video, audio, document, archive, mail, text
filegrail . --ext jpg,pdf         # exactly these
filegrail . --json | jq '.files[].origins[] | select(.block == "pdf-info")'
```

The `--type` families are derived from the readers themselves, so a format
added to a reader becomes selectable in the same commit. A test enforces that
too.

---

## Adding one

[`CONTRIBUTING.md`](../CONTRIBUTING.md) has the bar for a new reader. The short
version: one module per container family under `src/filegrail/sources/embedded/`,
a test that builds a minimal valid file rather than committing a sample, and no
byte length counted by hand.

Then add the row here. A missing row is a failing test, so you will not forget.
