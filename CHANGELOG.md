# Changelog

All notable changes to `filetrail` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
the project uses [semantic versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Changed

- Modes are commands now, not flags: `filetrail explain FILE`,
  `filetrail compare A B`, `filetrail doctor`, `filetrail menu`,
  `filetrail help <command>`. `--doctor` and `--explain` were modes wearing an
  option's clothes - each ignored most of the other options, and every pair of
  them was mutually exclusive, which is exactly the shape subcommands exist to
  express. `filetrail <path>` still scans with no command word, because that is
  what people do most of the time and making them type `scan` would be ceremony.
- `-v`, `-j` and `-h` short forms; the landing screen is the conventional
  usage / examples / commands / options shape, so a reader who has used any
  modern command-line tool can read it at a glance. The evidence-source table
  moved off it into `doctor`, where the question has actually been asked.

### Added

- Files in one scan are linked to each other by the identifiers XMP carries for
  exactly that purpose. A master, the export made from it and the web rendition
  made from that now say so in the report, in both directions - `derived from`,
  `source of`, `descends from`, `original of`, `same document`.

  A shared original document is reported as a common ancestor and never as a
  derivation. The corpus explains why: `osint360-klienci-zastosowania.pdf`
  carries an `xmp:CreateDate` of 2013 inside a document made in 2026, because a
  LibreOffice template dragged its whole XMP block along. Everything ever made
  from that template shares an original and shares nothing else. For the same
  reason an identifier shared by more than eight files is counted rather than
  paired off - that is a template sitting under a directory, not a lineage, and
  pairing it would be a square number of links saying nothing.

  Two guards worth naming. Half of a `DerivedFrom` reference is looked up only
  in its own index, because PowerPoint writes one uuid as both the document and
  the instance and matching across the two would make each of its exports an
  instance of the rest. And a null uuid identifies nothing, so it joins nothing:
  it is what a writer emits when it has nothing to say.

  A link is not an origin. An origin is one source's claim about where a file
  came from; a link is a relation between two records that exists only because
  both were scanned together, so it lives on the record rather than among the
  claims. An ancestor's download record is deliberately *not* inherited down a
  derivation edge - an archive inherits because the bytes were literally inside
  it, and an edited export is a different file. `docs/specs/` has the reasoning.

  The developer's corpus produces no links at all: 105 files, twenty identifiers
  and not one of them shared. That is the honest result for a collection of
  unrelated downloads, and the feature was verified instead against a chain
  written by `exiftool`.

- Reconciliation now compares a camera's own tags against their XMP mirror, the
  way it already compared IIM against XMP. The pairing is the XMP
  specification's own - the `tiff:` and `exif:` properties are defined as the
  serialisation of those tags - so a difference is one of the two blocks having
  been rewritten rather than two tools writing one fact differently.

  What is compared is what the camera said about taking the picture: the make,
  the model, the software, the artist, the lens, the body serial number, the
  description, and the two capture timestamps. Exposure settings are left out on
  purpose. XMP writers put units, rationals and comma decimals in them - `f/5,6`
  against 5.6, `1/500 sec.` against 0.002, `105,0 mm` against 105 - and a
  comparison that cannot read those would report a contested attribution on
  almost every photograph ever taken. `xmp:ModifyDate` against EXIF `DateTime`
  is left out for the opposite reason: tools maintain one and not the other, so
  the two drift apart in ordinary use and a finding there would say nothing
  while diluting the ones that do.

  Timestamps are compared as moments rather than as characters. EXIF writes a
  local reading with no zone, XMP writes the same reading with an offset
  attached, and IIM writes a bare eight-digit day - three spellings of one fact.
  Comparing their characters would have found conflicts in three of the
  twenty-two files in the developer's corpus that carry two self-descriptions,
  and every one of them would have been invented. That also fixes a conflict the
  IIM comparison could already have reported and nobody had a file to trigger:
  `DateCreated` as `20190304` against `2019-03-04T10:22:31+01:00`.

  A finding now carries the two blocks it is between, so the conclusion names
  them instead of talking about the IPTC block of a file that has none, and a
  consumer reading the JSON does not have to parse the sentence to learn which
  two pieces of evidence disagree.

- The broadcast extension, `bext`, which is what a field recorder writes into
  a WAV: the machine that made the recording, the moment it started, a slate
  line for the take, and the coding history - one line per processing step, so
  a take that went through an analogue deck before it was digitised says so on
  its first line. The lines are kept apart, because the chain is the evidence
  and folding it into one sentence loses where each step began.

  Where a file has both, the recorder is named first and the editor after it -
  "Sound Devices MixPre-6 (edited with Adobe Audition 3.0)" - for the reason
  the EXIF reader already names a camera before the software that processed
  its picture. Naming only the last writer hands back the studio and loses the
  field. The recording moment likewise outranks the date the editor wrote.

  It stays at `document-metadata` rather than being promoted to
  `device-metadata`. `Originator` is free text and is a recorder about as often
  as it is a company, and a reader cannot tell which from the file.

- RIFF `LIST/INFO`, which is where a WAV or an AVI records who edited it.
  `ISFT` names the software, `ICRD` the date, `IART` and `IENG` the people
  credited; the twenty-odd remaining codes are kept under their published
  names, or under the code itself where a writer invented one.

  This began as a repair rather than an addition. `.wav` was on the ID3
  reader's list of extensions, and that reader requires the tag at byte zero
  while a WAV begins with `RIFF` - so the format was advertised and could never
  return anything. A WAV that does carry an ID3 tag keeps it in a chunk, which
  is read there now, and `.wav` has left the ID3 reader's list, because the
  claim it made was false.

  AVI arrives with it and costs nothing: the container is the same list of
  chunks and the INFO block is the same block. In a large file it sits after
  the frames, so the walk seeks over payloads instead of reading them - three
  megabytes of video cost 0.08 ms - and it does not descend into the lists
  holding sample data. Anything at all can appear inside a frame, chunk headers
  included, and a file must not be able to forge its own provenance in its own
  payload.

  Verified against files written by ffmpeg and by alsa-utils, including one
  carrying no metadata at all, which is reported as carrying none. The `id3 `
  chunk is the exception: nothing available here writes one, so that path rests
  on the specification and on constructed files.

- Reconciliation reaches what a file says about itself. IPTC and XMP hold the
  same facts under different names - Adobe published the pairing when it moved
  IIM into XMP - and an editor maintains the XMP while leaving the IIM block as
  it found it. Two photographers in one file is therefore not a formatting
  difference but the trace of an attribution being changed, and until now the
  report printed both without a word and left the reader to notice.

  Agreement stays silent. One editor writing both blocks at once and keeping them
  consistent is the ordinary case, and a line on almost every photograph would
  say nothing. Only the difference is reported, as `attribution_conflict`, and
  the conclusion names what disagrees while saying plainly that which side was
  rewritten is a question it can raise and not answer.

  A contested file now brings both self-descriptions on screen, for the reason
  the report already brought forward a conflicting acquisition record: a verdict
  about evidence the reader cannot see is not a verdict. The block is headlined
  `contested attribution` rather than the acquisition state, which described
  something else entirely and was printed in the colour of good news.

- IPTC IIM, read from the Photoshop image-resource block that carries it - which
  means JPEG, TIFF and PSD from one search, because the block is the same
  structure wherever it is embedded. TIFF gets a second path: some writers store
  the datastream directly in tag 33723 with no Photoshop block around it, and
  there is no marker to search for then - a datastream begins `\x1c\x02`, two
  bytes that would match almost anything - so that one is reached through the
  directory. IIM is what a newsroom writes into a picture: who took it, who is to
  be credited, where it was taken and under what terms it may be used.

  Ranked at 51, just below XMP. The two hold the same kind of self-description
  and IIM is the older of them; modern tools maintain the XMP and leave the IIM
  block as they found it, so a byline there is frequently a record of an earlier
  state of the file rather than its current one. That makes it the weaker claim
  and, for exactly the same reason, evidence worth keeping.

  Two details a specification-shaped reader gets wrong. IIM predates Unicode, so
  a block that does not declare UTF-8 in record 1 holds single-byte text, and
  decoding it as UTF-8 turns every accent into a replacement character - losing a
  byline rather than reading one. And a length with its top bit set is not a
  length: the remaining bits count how many bytes the real length occupies, which
  is how a caption longer than 32767 bytes is carried. Reading that as an
  ordinary length does not skip one field, it loses the reader's place in the
  stream and every dataset after it.

### Changed

- A place and a coordinate are two fields now. `geo` holds a latitude/longitude
  pair this tool decoded itself, from EXIF or an ISO 6709 atom; `location` holds
  a place written as a name. They had shared one field, which was tolerable while
  every coordinate arrived already decoded and became untenable the moment IPTC
  turned up recording "Firenze, Italy" and meaning it. A decoded fix can be put on
  a map; a typed name is a claim like any other text, and a report that prints
  them on the same line has stopped saying which it has.

  `--json` gains a `geo` key, and `location` no longer carries coordinates.
  `--identify` reads its trusted coordinate pair from `geo`, which is also the
  name it has always used for that identifier - one word for one thing, in the
  claim line and the identifier list alike.

- XMP, read from wherever a container embeds the packet: JPEG, TIFF and raw,
  PNG, PDF, MP4, HEIC, SVG. EXIF says which camera made a photograph. XMP is the
  only metadata standard in wide use that says what happened to it afterwards,
  and it keeps that as a sequence rather than one field - so `xmpMM:History`
  becomes one claim per recorded edit instead of a flattened list, and an editing
  sequence lands on `--timeline` beside the download that brought the file in.

  An edit that records no time stays a field rather than becoming a claim: the
  timeline supplies a file's own timestamps to a claim carrying none, which would
  place an editing action at a moment nothing recorded. Ranked at 52, between a
  camera naming its own model and a bare document property, because an editor
  writing free text about itself is the weaker claim of the two. The packet is
  located by its root element rather than by a path through each container, which
  is what lets one reader serve every format that embeds one - and what let the
  local corpus find the two defects a specification-shaped fixture could not: a
  root element under an unexpected prefix, and a namespace spelled without its
  trailing slash. Signatures do not enter into it. XMP has none.

- PNG text chunks no longer repeat the raw XMP packet. It arrived clipped at 4096
  characters, so what reached the field tree was unparseable markup sitting beside
  the properties the XMP reader now decodes out of it.

- `--identify` knows a software field by its name whatever namespace precedes it.
  The guard that keeps `LibreOffice 25.2.3.2` out of the address list matched
  `Producer` exactly, so `pdf:Producer` walked straight past it - as did
  `exif:GPSVersionID`, which reads 2.2.0.0 in almost every geotagged photograph
  ever taken and has never been an address.

- `filetrail compare A B`: what two files record about themselves that agrees,
  what differs, how each one arrived, and how far apart they claim to have been
  created. Two files can share an earlier life without sharing an acquisition
  path, and that combination - one camera, two routes - says something neither
  file says alone. It reports what agrees; it never concludes that two files are
  "the same".

### Added

- `--explain`, for one file. The report answers *what do we know*; this answers
  *why should I believe it*, which is the question that decides whether a finding
  can be used. It adds no data. It lays out every record under the question it
  answers, names the ones that support each other and the ones that contradict
  each other, and draws the conclusion in sentences - so that a reader can
  disagree with it. A verdict nobody can argue with is a verdict nobody should
  trust.

- Evidence strength replaces the bare number on the meter line: `direct`,
  `inherited`, `credentialed`, `self-reported`, `circumstantial`, `weak`.
  Printing `55` invited it to be read as a probability, which it never was -
  there is no statistical basis for `55`, only a defensible ordering of how
  directly a source knows what it claims. The number still ranks sources against
  each other and still appears in `--json`.
- A download record matched to a file by name is now checked against the size
  the record kept. A size that agrees is corroboration the name alone cannot
  give; one that disagrees very likely means the record is about a different
  file that happens to share the name, and the reconciliation says so.
- The desktop's recently-used list, read from the freedesktop
  `recently-used.xbel` every GTK application writes. It names the application
  that opened a file and when - the graphical equivalent of shell history, and
  ranked just below it, because opening a file proves contact rather than
  acquisition.

- `--doctor`, which reports what this machine can be asked before anything is
  asked of it: which browser profiles are readable and how many records they
  hold, whether this filesystem carries extended attributes (tested, not assumed
  from the platform), whether the shell kept timestamps, whether creation times
  exist, and how far back the browser records reach. `no recorded origin` can
  mean the evidence was searched and the file was not in it, or that the
  evidence was never there to search, and a reader who assumes the first when
  the second is true has drawn a conclusion the tool never supported.

- Reconciliation between acquisition records. Where two independent sources say
  how a file arrived, the report now says whether they agree, agree only about
  the host, or contradict each other, and prints what each one claims. It also
  flags a file whose own metadata reports a creation time *after* it arrived,
  and a download record that was tied to the file by name rather than by path.
  A disagreement brings every acquisition record on screen without `--verbose`,
  because a verdict that refers to evidence the report hid is not a verdict. A
  single uncorroborated record - the ordinary case - is left unannotated, since
  a label on every entry says nothing. `--json` carries the verdict too.

### Fixed

- A downloaded file no longer loses everything it recorded about itself. Claims
  were ranked against each other by confidence and only the winner printed, so a
  browser download record (90) silently deleted a camera's EXIF (55) - and with
  it the capture time, the body serial number and the GPS fix, which is usually
  the most valuable thing in the file. Acquisition and intrinsic provenance
  answer different questions and are now both printed, acquisition first.
  `--verbose` still shows every claim.

### Changed

- Nothing in the report is truncated any more. A value too long for the line
  wraps onto the next one instead of ending in an ellipsis - the file name, the
  origin, the source line, every labelled fact and every field. A cut-off value
  is one the reader has to go and fetch another way, which defeats having read
  the file at all.
- Every decoded field is printed by default, as a tree (`+-` / `\\-`) hanging off
  the claim it belongs to. `--full` is gone; `--brief` collapses the tree back to
  a summary for anyone scanning a large tree.
- Gutter glyphs are padded to a common width. The ASCII arrow is `<-`, two
  characters, so the left edge previously stepped sideways in ASCII mode and one
  wrapped line ran a column past the terminal width.

### Fixed

- HEIC, HEIF and AVIF now yield their EXIF. The reader took the first
  `Exif\0\0` in the file, but encoders write that as the item type in the
  `infe` entry, so it found the item table and decoded nothing — every file in
  the family came back empty. It now scans on until a TIFF header follows the
  marker. A Nokia 8.3 sample that previously reported nothing now reports its
  software, its capture time and its GPS coordinates.
- The SVG generator comment is read again. Its pattern held `{3,120?}`, which
  is not a quantifier — the `?` sits inside the braces — so Python matched the
  literal text and the Illustrator and Matplotlib comments never resolved. Only
  the Inkscape attribute path was tested, so a green suite hid it.

### Added

- Every metadata field a reader decodes is now kept, not just the handful the
  report summarises. `Origin` carries them structured and named, `--json` always
  includes them, and `--full` prints them in the terminal. A geotagged JPEG went
  from four reported facts to fifty: EXIF integer types were never decoded at
  all, so `BodySerialNumber`, `GPSTimeStamp`, `GPSAltitude` and `Orientation`
  were invisible. PDF now reads `Title`, `Subject` and `Keywords`; OOXML and ODF
  take every property their parts declare, which is where `revision`,
  `lastPrinted`, `TotalTime` and `editing-duration` live. `--redact` sweeps the
  new fields, because a tag like `UserComment` is free text and can hold a
  credential.
- `--identify`, which pulls the emails, domains, URLs, IPv4 addresses,
  cryptographic hashes and geographic coordinates out of the metadata a scan
  already read, deduplicated across files and each one carrying the file and
  field it came from. The detectors are ported from DirSifu (MIT, same author),
  including what they deliberately refuse to match. One rule is new here: a
  dotted quad or a build hash inside a field that names software is a version,
  not an address - this corpus is made of strings like
  `LibreOffice/24.2.7.2$Linux_X86_64`, and the field name is known, so the
  question can be settled rather than guessed.
- `--type` and `--ext`, to narrow a scan to the file types you care about.
  `--type image` beats listing the twenty-five extensions the word stands for,
  and the families are built from the extension sets the readers already
  declare, so teaching a reader a new format also teaches the filter. The filter
  is applied while walking, before a file is opened, hashed or parsed. An empty
  result names the filter rather than reading as "this folder holds nothing".
- A landing screen. `filetrail` with no arguments now introduces itself - name,
  version, author, repository, licence, worked examples and the sources it reads
  with their confidences - instead of silently scanning the current directory.
  Starting an unasked-for scan of wherever the shell happens to be is a surprise,
  and in a home directory an expensive one; the screen says `filetrail .` for the
  folder you are standing in. `--about` prints it again from anywhere. Nothing on
  it waits for input, so it works piped and in a script.
- An interactive front end, `filetrail --menu`, for choosing a view without
  memorising flags. It is printed text and `input()` rather than curses, so it
  keeps the zero-dependency promise and works over SSH and on Windows. It
  refuses to start when output is redirected, and it prints the `filetrail`
  command it is about to run — a menu should make itself unnecessary.
- Legacy Office documents. A `.doc`, `.xls` or `.ppt` is a compound file, and
  the two property-set streams every Office release has written since 1995 give
  the application, the author, the last editor, the company, the title and the
  creation date. Both the regular sector chain and the mini stream are followed,
  because a spreadsheet pads its summary to the cutoff while a Word document
  does not. Still no runtime dependency: the container reader is standard
  library throughout.
- `tests/test_corpus.py`, which runs against real files in `test-data/` when
  that directory exists and skips when it does not. It asserts that a decodable
  EXIF payload, or a compound document's summary, never comes back empty,
  whatever container holds it. Both fixes above are the class of defect a
  synthetic fixture cannot reach.

### Changed

- Redesigned the terminal report, and wrote the system down in
  [`DESIGN.md`](DESIGN.md) so it can be argued with. Entries are bound together
  by a one-character gutter (`●` a file, `←` its origin, `│` a continuation)
  instead of drifting indentation; colour now encodes only *which class of
  source* made a claim, so five colours learned once let a folder be triaged by
  eye; findings are ordered strongest evidence first, and grouped under headings
  once a class actually collects more than one file. The summary is an aligned
  table rather than a run-on line, and the masthead carries a coverage meter.
- Colour depth is detected rather than assumed: TrueColor when `COLORTERM` says
  so, 256 otherwise, and a 16-colour fallback for terminals that have neither.
- No rendered line can exceed the terminal width. Every right-aligned column now
  clips the text beside it first, which is enforced across six widths and both
  glyph sets by `tests/test_layout.py` — a wrapped line was previously possible
  on a narrow window and nothing would have caught it.
- Timestamps in the unexplained-files column are trimmed to the second.
- Renamed the project to `filetrail`. The previous name was crowded on GitHub,
  including one repository that is the same tool by concept.
- `--no-recurse` is listed in the README, having been implemented but not
  documented.

## 0.1.0

The first working version. It reconstructs where files came from by reading
records that already exist, rather than asking anyone to wrap their commands.

### Sources

- Browser download history for the Chromium family and Firefox: originating
  page, referrer, redirect chain, timestamp and size. Profiles are copied before
  being read, so a running browser is neither disturbed nor modified.
- Operating system origin metadata: the Windows `Zone.Identifier` stream, the
  macOS `kMDItemWhereFroms` attribute and the Linux `user.xdg.origin.url`
  extended attribute.
- Archive membership, so files extracted from a downloaded archive inherit its
  origin instead of losing it.
- Embedded metadata from more than twenty formats: EXIF for JPEG, TIFF and its
  raw variants, WebP and HEIC, **including GPS coordinates**; PNG text chunks,
  which carry the producing software and the prompt recorded by generative
  tools; MP4 and MOV atoms; PDF `Info` dictionaries, including compressed object
  streams; Office Open XML and OpenDocument; EPUB, RTF, SVG, Jupyter notebooks
  and ID3 frames.
- C2PA Content Credentials, read from the JUMBF manifest in PNG and JPEG, which
  report the producing application and whether a model generated the file. The
  signature is not verified and every claim says so.
- Shell history, at low confidence, as corroboration only.
- Filesystem creation and modification times, via `statx(2)` on Linux.

### Output

- A styled terminal report, hand-rolled so the tool keeps no runtime
  dependencies, degrading to the same layout in plain text when piped, under
  `NO_COLOR` or `TERM=dumb`, and to ASCII where the glyphs cannot be printed.
- `--json` for machine-readable output, `--timeline` for a chronological view,
  `--unknown-only` for files nothing accounts for.
- `--redact`, which strips credentials from URLs, referrers and commands and
  replaces each with a short non-reversible fingerprint.
- An explanation when nothing matches, rather than a bare zero, because a
  pruned browser history is missing evidence and not a malfunction.
