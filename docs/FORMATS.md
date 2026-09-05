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
| `c2pa` | `.jpg` `.jpeg` `.png` | JUMBF manifest: producing application, creation data, digital source type, and whether the manifest's own hash still covers the file |

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
| `xmp-history` | The same packet | Every recorded editing step. A step with a timestamp becomes its own dated claim and lands on `--timeline`; one without stays a field, because inventing a time for it would be worse than leaving it undated. The sequence is also held against itself: a step dated before the one it follows is reported |
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

## Torrents

A torrent is a container in the same sense an archive is: it lists its members
by name and exact size, so a file matching both was very likely one of them.
Unlike an archive it carries an origin of its own rather than one to inherit.

| File | What comes out |
|:---|:---|
| `.torrent` | The trackers it was announced to, the client that wrote it, any comment, and a magnet address built from the info hash |

Torrents are read from the scanned tree and from the stores the clients keep -
qBittorrent's `BT_backup`, Transmission's `torrents`, Deluge's `state` - which
is the ordinary case, since a downloaded file rarely has a `.torrent` beside it
and the client has kept one all along. `filegrail doctor` says whether any such
store was found.

The info hash is taken over the `info` value exactly as its author wrote it,
not over a re-encoding of what was decoded: the two differ wherever the author
was not canonical, and that is precisely where a hash computed from the
re-encoding would name the wrong content. The decoder refuses non-canonical
bencode for the same reason.

The claim is not dated. A torrent's creation date says when the torrent was
made, which can be years before anything in it was fetched, so the date is
reported as what it is rather than as an arrival.

---

## Sidecars

Not metadata either, and not inside the file at all. A download tool can be
asked to write what it knows beside what it fetched, and that record names the
page the bytes came from.

| File | What comes out |
|:---|:---|
| `<name>.info.json` | `yt-dlp --write-info-json`: the page URL, the uploader and channel, the publication date, the extractor, and the moment the fetch ran |

The moment reported is the fetch, not the publication. `epoch` is when the tool
wrote the document; `upload_date` is when the video became available and can be
years earlier, so reading it as the arrival would place the file on this
machine before it was.

The estimated size is deliberately not carried. `filesize_approx` is an
estimate for the format that was chosen, and reported as a byte count it would
contradict the file on disk and be reported as a size mismatch nothing is
actually wrong about.

A sidecar is paired to its media by file name alone, which is why it ranks
below the attributes an operating system attaches to the file itself: a copy
that brings one and not the other, or a rename, breaks that pairing in a way an
extended attribute cannot be broken.

---

## Archives

Not metadata. These are read so that a file extracted from one can inherit the
archive's origin, when the member name and uncompressed size both match.

| Extensions | What filegrail does with them |
|:---|:---|
| `.zip` `.jar` `.whl` | Member names and uncompressed sizes |
| `.tar` `.tgz` `.gz` `.bz2` `.xz` | The same, through the compression |

The files inside are also read, one at a time, without unpacking the archive:
a photograph in a zip has the same EXIF it would have on disk. That claim is
about the **archive**, so the member's moment and its coordinates do not
survive into it - a photograph taken in 2008 inside a zip written last week
does not date the zip, and a zip has never been anywhere. Both keep saying what
they say in the fields, under the member's name.

For the same reason the readers that sweep raw bytes for a block, XMP and IPTC,
are not run on an archive at all. What they would find there belongs to a
member, and a zip is not made by Photoshop because a photograph inside it was.

The archive is considered whether or not it is inside the scanned tree — a case
directory is usually the *result* of unpacking something that lives elsewhere.

---

## Text a document holds

A different axis from everything above. The tables so far are what a file
records *about itself*; this is what it *says*, and it is read only when
`--content` asks for it. The identifier detectors are then pointed at the text
as well as at the metadata, and every value carries which of the two it came
from, and where in the document it was.

Nothing here is a claim about provenance. A body is not evidence of arrival.
The point of reading it is the correlation: a name a document carries that the
record of the file's *arrival* also carries was written down twice, by two
separate acts, and neither half says that alone.

| Extensions | What is read |
|:---|:---|
| `.txt` `.text` `.md` `.markdown` `.rst` `.log` | The file, a line at a time, and the line is what a value is reported against |
| `.csv` `.tsv` `.json` `.ndjson` `.jsonl` `.ipynb` `.yaml` `.yml` `.toml` `.ini` `.cfg` `.conf` `.vcf` `.ics` | The same. Data formats are text, and an export out of an application is exactly the sort of file an examiner is handed |
| `.html` `.htm` `.xhtml` `.xml` `.svg` | The text, and the addresses in `href`, `src` and their kin, by the line of the file. `<script>` and `<style>` are left out - a colour is a short hex digest and a bundler writes hosts nobody typed - and a namespace declaration is markup rather than something the document said |
| `.docx` `.docm` `.dotx` `.xlsx` `.xlsm` `.xltx` `.pptx` `.pptm` | The body, footnotes, endnotes and comments of a Word file; every slide and its notes; a workbook's shared strings and its inline cell text. Reported as `body`, `footnotes`, `slide 4`, `sheet 2` - the terms the format has. There is no page number: pagination happens when something renders the file, which does not record where the breaks fell |
| `.odt` `.ods` `.odp` `.odg` `.odf` `.ott` `.otp` | `content.xml` as the body, `styles.xml` as headers and footers |
| `.epub` | Each chapter, under the name the book gives it |
| `.eml` `.msg` | The message body, decoded first - quoted-printable and base64 both hide an address from anything reading the bytes as they lie. The headers are not taken again here: they are already read as evidence of delivery, and counting them twice would file the second copy under the wrong axis |

No dependency comes with any of this. The formats where a text search fails
hardest are zip archives of XML, and the reader that already opens them for
their properties opens them for this, under the same bound on what one member
may cost.

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
| Who put a file in a synced folder | Dropbox encrypts its file cache, and for every client read here the answer lives on the server rather than on this machine. The folder and the account it syncs with are read; **who added the file is not** |
| Messaging-app stores | Telegram Desktop encrypts `tdata` and keeps no chat history in it. Signal Desktop's `db.sqlite` is SQLCipher behind a key the operating system wraps, and opening it needs a crypto library this tool does not carry. Discord and Slack keep no local message database. **No claim here names a sender or a conversation** - only the file names those clients write, which is a much weaker thing and is ranked as one |
| Vendor maker notes | Every manufacturer encodes them differently and each needs its own parser. The rest of EXIF is decoded |
| C2PA signatures | The certificate chain is **not** verified; that needs a crypto library and a trust list that changes over time. The *hard binding* is checked, which is a different question - whether the manifest describes these bytes, not whether its signer is anyone you should trust |
| `.mbox` | Many messages, one record per file. There is no honest single claim to make about a mailbox |
| Jump Lists (`.automaticDestinations-ms`) | In the Recent folder beside the shortcuts, and a different format. Shortcuts first |
| Fixed-length MAPI properties | Delivery and submit times live in `__properties_version1.0`, not a `__substg1.0_` stream. Left unread rather than guessed at, with no real `.msg` to check the layout against |
| PDF text | The only format `--content` does not read. Pulling the string literals out of a content stream is an afternoon's work that produces readable text for perhaps half of real documents and mush for the rest, and a confident wrong answer is worse than an absent one here. Metadata **is** read from a PDF; only its text is not |
| Source code as text | A checkout is thousands of files whose identifiers are dependency hosts and licence URLs. `SKIP_DIRECTORIES` keeps a scan out of `node_modules` on the same principle |
| RTF text | Text under a layer of control words and hex escapes. It needs a parser to read honestly and yields noise without one. RTF **metadata** is read |
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
