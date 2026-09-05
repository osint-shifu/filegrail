# Changelog

All notable changes to `filegrail` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
the project uses [semantic versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- `Zone.Identifier` is read on machines that are not Windows. It is the richest
  thing Windows writes down about a download - the address, the referrer and
  the zone the bytes came from - and it was reachable only from Windows, which
  put it out of reach of the one workflow built to want it. `--home` exists for
  reading a profile off a mounted image, and an examiner doing that is not
  running Windows.

  Nothing exotic is needed to get at it. `ntfs-3g` maps named data streams into
  the `user.` namespace and does so by default, so the stream is simply
  `user.Zone.Identifier`; Samba's `vfs_streams_xattr` stores the same bytes
  under a prefix of its own, and both spellings are read. The named-stream
  syntax is still only asked for on Windows, because a colon is a legal
  character in a POSIX file name and trying it elsewhere could open a file that
  merely happens to be called that.

  `doctor` gained a row for it, since a scan can now read a source `doctor`
  never mentioned.

### Fixed

- `LICENSE` is the Apache License 2.0. It had been reflowed and cut by about a
  third: the APPENDIX was gone and so were normative sentences from section 1,
  including the whole definition of what a "Contribution" is - *"means any form
  of electronic, verbal, or written communication sent to the Licensor"*, and
  the clause excluding communication conspicuously marked otherwise. 1078 words
  where the licence has 1581.

  Nothing about that is cosmetic. `pyproject.toml`, the README badge and the
  metadata on PyPI all say Apache-2.0, and the file under that name said
  something else, which is why GitHub reported the repository as carrying no
  licence at all and why the same shortened text was shipping inside the wheel.
  Section 4 of the licence asks that recipients be given a copy of *the*
  Licence; a copy with clauses removed is not one. A tool that lists
  `Intended Audience :: Legal Industry` can least afford this particular bug.

  The text is now verbatim from `apache.org`, and a test pins its sha256 beside
  the licence the package declares - one licence stated twice, held together
  the way the version already is.

- A crafted document no longer costs what it says it does. ODF, OOXML and EPUB
  keep what they say about themselves in a named part inside a zip, and those
  four parts were read with `ZipFile.read`, which returns as much as the
  member's header declares. XML deflates at roughly fifteen hundred to one, so
  a **780 KB `.docx` whose `docProps/core.xml` declared 601 MB took 1.2 GB of
  memory and four and a half seconds** - allocated twice, once as bytes and
  once as the tree parsed from them. A directory of them is an out-of-memory
  kill. The same file now costs 33 MB and a tenth of a second.

  Every member goes through `read_part`, which reads through `ZipFile.open`
  with a bound on the decompressed stream and so needs no agreement between
  what the archive claims and what it holds. The bound is four megabytes, the
  same figure the PDF reader already allowed itself for inflated object
  streams; real property parts are kilobytes, and the ones that are not are not
  property parts. A test reads the modules' own source and fails on a bare
  `archive.read(`, because the thing to hold is the absence of a call and any
  test that lists today's sites would miss tomorrow's.

- A TIFF is parsed where it lies instead of being read into memory. `.tif`,
  `.tiff`, `.dng`, `.nef`, `.cr2`, `.arw`, `.orf` and `.rw2` all come through
  the TIFF path, and it was the one reader in the tree without a bound of any
  kind: a 419 MB file took 433 MB to answer with a few hundred bytes of tags,
  and a directory of raw frames from a camera is the ordinary case rather than
  an attack. It now takes 23 MB, which is the interpreter.

  Mapping rather than a window over the head, because an IFD offset may point
  anywhere in the file and a window would be wrong rather than merely smaller.
  The reader gained a way to fail it did not have - an empty file cannot be
  mapped, where reading one returned an empty string - so `read_exif` is now
  tested directly for that case and not only through the dispatcher whose net
  would have hidden it.

- `clean` no longer loses files. Every copy was written straight into `--out`
  under the file's own name, so two folders each holding a `photo.jpg` produced
  one copy: the second replaced the first, and the report said two files had
  been cleaned while one existed. That is the worse half of it. Somebody strips
  metadata from a tree of photographs, reads a summary that says the work is
  done, and publishes a directory that is missing files.

  A copy now mirrors the tree it came from - `case/a/photo.jpg` is written to
  `out/a/photo.jpg` - which is what keeps two files sharing a name apart.

- `clean` does not write over a file that is already at the destination path.
  The destination is a directory the user chose and may hold work of their own;
  an unrelated file with a colliding name was replaced without a word. It is
  now reported and skipped, and `--overwrite` asks for the old behaviour. This
  is the one command in the project that writes a file, so removing one nobody
  asked about is the failure it can least afford.

- `--redact` reaches `explain` and `compare`. It had only ever been a scan
  option, and `explain` is the command that prints the most of what it would
  remove: its whole purpose is to show every source behind a finding, including
  the ones that disagree, so a download URL carrying a session token reached the
  terminal in full. `compare` prints the route each file arrived by, which is
  the same URL. Asking either for `--redact` did not print an unredacted report
  — it failed with `unrecognized arguments`, which is the better half of the
  bug, but a user who has learned the flag on `scan` has no reason to expect
  the command that shows more to offer less.

  The flag now lives in a parent parser beside `--home` rather than in
  `_common()`, because it belongs to the commands that render evidence and to no
  others. `doctor` reports which sources exist and `clean` reports file names
  and the blocks taken out of them; neither can carry a credential, and an
  option that does nothing there would read as a promise.

## 0.3.0 - 2026-09-05

### Added

- `filegrail clean` writes copies of files with their metadata removed. JPEG
  segments, PNG chunks, the `udta` and `meta` atoms of an ISO base media file
  along with the two timestamps in its movie header, and the property parts of
  the zip-based Office and OpenDocument formats. `--type` and `--ext` narrow it
  the way they narrow a scan, so a directory can be cleaned one format at a
  time.

  **The original is never touched.** This is the only command that writes
  anything, and the rest of the tool rests on not writing, so copies go to
  `--out` - which is required, and refused if it sits inside the directory
  being read.

  Every copy is then read back with the readers that find metadata in the first
  place, and whatever they can still see is reported. A stripper is written per
  format and a format can carry a block somewhere it does not reach: a packet
  appended after a JPEG's end marker survives, and the check is what says so
  rather than leaving somebody to publish on the strength of the word
  *cleaned*.

  Two decisions worth stating. A movie is not shortened - its sample tables
  address the media by absolute offset, so the metadata atoms keep their length,
  become `free` boxes and have their payloads overwritten. And a document's
  property parts are emptied rather than deleted, because they are named in the
  package relationships and a part that is named and then missing is a broken
  document rather than a clean one.

  **PDF is deliberately not cleaned.** Without a library the only safe way to
  change one is an incremental update, which leaves the old `Info` dictionary
  physically in the file and merely stops pointing at it. For a cleaning tool
  that is worse than doing nothing, so it does nothing and says so.

### Changed

- The type annotations are checked. There were 362 of them and nothing verified
  any of them, which in a project that holds its format documentation against
  the readers with a test was the one large body of claims with no invariant
  behind it. `mypy` runs in CI now, against the oldest supported interpreter so
  that a construct newer than the floor fails here rather than on somebody's
  3.10.

  It found no defect a user would have met. What it found were annotations that
  were not true: `_origin` declared a required `block` for a value that is
  optional, one name stood for a tuple and a regex match inside a single
  function, and the tally table was typed loosely enough that calling its
  predicates was checked by nothing. Those are fixed rather than silenced.

  Only settings that already pass are enabled, because a flag nothing satisfies
  is a comment rather than a check.

## 0.2.0 - 2026-09-05

### Added

- Folders a sync client keeps in step with an account are read - Nextcloud,
  Dropbox, Syncthing and the Linux OneDrive client - and a file inside one is
  reported as being inside it, with the account or server named where the
  configuration names it.

  Two limits are worth stating rather than discovering. **Who put the file
  there is not readable**: Dropbox encrypts its file cache, and for all of
  these that answer lives on the server. And **sync runs both ways** - a file
  in a synced folder may have arrived from the account or may have been made
  here and pushed to it, and containment cannot tell those apart. So this is
  recorded as something that handled the file rather than as an account it came
  from, which is what is actually known.

  Containment is decided by path components rather than by text, because
  `Nextcloud-old` is not inside `Nextcloud` and comparing the two as strings
  says that it is.

  `doctor` reports which clients are configured and how many folders they name.

- The files inside an archive are read for their metadata, one at a time and
  without unpacking it. A photograph in a zip has the same EXIF it would have
  on disk, and none of it was being read; the archive was known only by the
  names and sizes it listed.

  The claim that comes back is about the **archive**, and that is the whole
  difficulty. The member's moment and its coordinates do not survive into it: a
  photograph taken in 2008 inside a zip written last week does not date the
  zip, and a zip has never been anywhere. Both keep saying what they say in the
  fields, under the name of the member they came from.

  Members are read by the ordinary readers rather than by anything new, so no
  format is understood twice. Only members a reader claims are opened, only
  below a size, and only the first twenty-five: the section says what kind of
  thing is in there, and an archive of ten thousand photographs is not read ten
  thousand times to say it.

- A `.torrent` is read for the files it distributes. It lists its members by
  name and exact size, which is the pairing the archive reader already makes,
  so a file matching both is given the torrent as an origin: the trackers it
  was announced to, the client that wrote it, any comment, and a magnet address
  built from the info hash.

  Unlike an archive member this is not an inherited origin. An archive passes
  on where the archive came from; a torrent states where the content came from
  itself, so every matching record gets it - including ones that already know
  something about themselves. A photograph with EXIF is no less interesting for
  also having been in a torrent.

  The clients' own stores are read as well as the scanned tree - qBittorrent's
  `BT_backup`, Transmission's `torrents`, Deluge's `state` - because that is
  the ordinary case: a downloaded file rarely has a `.torrent` beside it and
  the client has kept one all along. `doctor` reports whether a store was
  found, and the invariant holding the survey against the sources is what
  noticed that it had to.

  The claim is undated. A torrent's creation date is when the torrent was made,
  which can be years before anything in it was fetched.

  Reading one meant a bencode decoder, which joins the CBOR decoder as
  something the standard library does not provide and the zero-dependency rule
  will not import. It refuses non-canonical input rather than being lenient
  about it: an info hash is taken over the `info` value exactly as written, so
  bytes no honest encoder produced would hash to something that identifies
  nothing.

### Fixed

- `--type` lists every family it accepts. The help text was written by hand and
  `mail` had been added to the families without it, so `--type mail` worked and
  nothing said so. It is generated from the families now, and a test holds it
  there.

- An archive is no longer swept for XMP and IPTC blocks in its own raw bytes.
  Those readers look for a block wherever it turns up, and inside a container
  what they find is a member's - which is how a zip came to be reported as
  "made by Adobe Photoshop Elements" because a photograph inside it was. Now
  that the members are read under their own names, the sweep is both redundant
  and wrong.

## 0.1.0 - 2026-09-05

### Fixed

- The wheel can be built. `packages` already carried everything under the
  package directory, including the IANA TLD list, and the `force-include` entry
  added the same file at the same path a second time - which hatchling refuses,
  so **no wheel had ever been produced**. The entry rested on an assumption
  that turned out to be wrong, and nothing tested it because nothing had built
  the project. CI now builds it, checks the data file is inside, installs what
  it built and runs it.

### Added

- The file names messaging clients give to what they save are recognised.
  WhatsApp writes `IMG-20240115-WA0001.jpg` and its siblings for video, audio,
  voice messages, documents and stickers; Telegram Desktop writes
  `photo_2024-01-15_12-30-45.jpg`. A file carrying one came through that client
  far more often than not.

  It is worth being exact about what this is not. It names no sender and no
  conversation, because those stores cannot be read: Telegram Desktop encrypts
  `tdata` and keeps no chat history in it, Signal Desktop's database is
  SQLCipher behind an operating-system-wrapped key, and Discord and Slack keep
  no local message database at all. Reading any of them would mean a crypto
  dependency, which this project does not have. `FORMATS.md` says so where the
  rest of what is deliberately not read is listed.

  So this is a name and nothing else, and it is ranked below an application
  having opened the file - which at least happened. A name is typed as easily
  as it is written and is lost the moment somebody renames the file.

  The claim is left undated on purpose. The name carries a day, and for
  Telegram a clock with no zone on it, and putting either on the timeline would
  place the file at a moment nothing recorded. A pattern matching the shape but
  not the calendar - `IMG-20241315-WA0001.jpg` - is read as the coincidence it
  is and reported as nothing.

- The record `yt-dlp` writes beside what it fetched is read. `--write-info-json`
  leaves `<name>.info.json` next to the media, and that document names the page
  the bytes came from, the uploader and channel, the publication date, and the
  moment the fetch ran. It is an acquisition record in the plainest sense - the
  program that got the bytes wrote down where it got them - and unlike a
  browser database it travels with the file.

  It ranks below the attributes an operating system attaches to the file
  itself. A sidecar is a separate file paired to the media by name alone, so a
  copy that brings one and not the other, or a rename, breaks that pairing in a
  way an extended attribute cannot be broken, and nothing in the document
  proves it describes the file it happens to sit beside.

  The moment reported is the fetch and not the publication. `upload_date` can
  be years earlier, and reading it as the arrival would put the file on the
  timeline before it was ever on this machine.

  `filesize_approx` is not carried as a byte count. It is an estimate for the
  format that was chosen, and reporting it as the size would produce a size
  mismatch that nothing is actually wrong about.

- An editing history recorded out of order is reported. `xmpMM:History` is a
  sequence and the reader already keeps the order the encoder wrote, so a step
  dated before the one it follows contradicts the list it sits in - a clock
  moved, a zone was got wrong, or the history was written by something other
  than the sequence of events it claims to describe.

  It arrives as `impossible_order`, the same kind as a document modified before
  it was created, because it is the same class of problem: the file's own
  account of itself in an order that cannot have happened. Only the first
  inversion is reported - one is enough to say the account is unreliable, and a
  history that goes backwards usually does so repeatedly, which would bury
  every other finding about the file.

  Two steps at the same moment are not backwards. An application that saves and
  exports in one action writes both at the same second, and equal is not
  decreasing.

- `--cluster` groups the scan by the sources more than one file names. A
  directory is a list of files; a case is the smaller number of authors and
  cameras that produced them, and the section exists to turn the first reading
  into the second.

  Three axes, kept apart because they do not identify equally well. A body
  serial is assigned per unit and names one physical camera. A make and model
  names a product thousands of people own, which is a different claim and is
  never merged with the first - a reader told that two photographs "came from
  the same camera" on the strength of a model name has been told something the
  metadata does not support. An author field holds a name somebody typed, and
  two people can type one name.

  A field naming several authors is read as several. These formats separate
  them with a semicolon, and reading the value whole invented a person nobody
  is while hiding every real author in it - in the local corpus it split one
  author across three near-identical groups. A comma is deliberately not a
  separator: `Smith, John` is one person written surname first.

  The author fields are the ones the overview already counts rather than a
  second list beside it, so a block that learns to report an author becomes
  clusterable in the same change.

  It is on `--json` as `shared_sources`, with every path, and on the menu.

- A block whose own two timestamps run backwards is reported. Where a document
  records both when it was made and when it was last changed - a PDF `Info`
  dictionary, OOXML core properties, an XMP packet - and the change comes
  first, the block is contradicting itself. That needs no second source to be
  wrong, which is what makes it different from the timeline conflict already
  reported: that one is the file disagreeing with the machine it arrived on,
  this one is the file disagreeing with itself. It arrives as its own finding
  kind, `impossible_order`, so a consumer can tell the two apart without
  reading the sentence.

  Only pairs a reader actually emits are compared. A rule written for a block
  that records neither field could never fire, and so could never be found
  wrong.

  Two stamps are ranked only where they were written to the same standard of
  precision. One writer naming its zone while the other stays silent can differ
  by most of a day, and calling that an impossible order would be inventing the
  half nobody wrote down - so it is left alone instead.

  The verdict no longer heads such a finding with the acquisition state. A file
  whose dates run backwards has said nothing about how it arrived, and printing
  `no acquisition record` above the contradiction labelled one thing with the
  name of another; it now reads `contradicts itself`.

- The C2PA hard binding is checked. A manifest carries a hash of the asset it
  describes, with its own bytes cut out of the range so it is not hashing
  itself, and recomputing that hash needs no key, no certificate and no trust
  list - only the file. So a manifest lifted onto a different image, and an
  asset edited after its manifest was written, are both reported now, where
  before the tool could only repeat what the manifest said about itself.

  This is deliberately not signature verification and the report does not let
  the two be confused: a claim now reads `hash binding matches; signature not
  verified`. The first says the manifest is about these bytes. The second is
  still the open question of whether anyone should be believed about it.

  Finding the assertion meant reading JUMBF labels rather than guessing at
  payloads by their shape, so every box is now filed under the label its
  description box gives it. `c2pa.hash.data` is found by name, and an
  assertion that omits its algorithm inherits it from the claim, the way the
  specification says to.

### Changed

- The report carries the wordmark. It is redirected to a file more often than
  it is read on screen, and a `report.txt` that does not say what produced it is
  a wall of text somebody has to identify from memory. The banner is the landing
  screen's mark with the version, the tagline, the target and the scan
  statistics - and none of the repository, licence, usage or commands, because a
  report is not an introduction.

- The inventory counts formats rather than spellings. `JPG 20` beside `JPEG 1`
  was one format counted twice; `jpg`, `jpe`, `tif`, `yml` and `htm` fold to the
  name the format is usually called by, and `audit.tar.gz` is `TAR.GZ` rather
  than `GZ`, which said nothing the file name had not. Presentation only -
  `--type`, `--ext` and the record keep the extension the filesystem has.

- `findings` prints `metadata` and `acquisition evidence` even at zero. This
  tool stands on those two things, and a scan that read a great deal of the
  first and none of the second has found that out; leaving the row off made an
  answer look like an omission. `authors / creators` joins them, keyed on the
  block rather than on the field name - `Creator` is the application in a PDF
  Info dictionary and the person in OOXML core properties, and one flat list of
  names would have counted every PDF's typesetter as its author. `dated claims`
  is `timestamps`, and identifiers are counted in identifiers rather than files.

- `attention` is `notable findings`, and it no longer uses `●`. Coordinates and
  Content Credentials are findings, not problems, and the heading said
  otherwise. `●` means *this is a file* everywhere else in the report, so
  spending it on a count line cost the gutter the one symbol it has for that;
  only the contested `!` keeps a glyph. `carry` became `contain` throughout.

- Every file with no findings is listed by default. `--limit` defaulted to 25
  and hid the rest behind a line saying how to see them, which is the same
  objection that put every decoded field on screen without asking: nobody should
  run the tool twice for data it had the first time. `--brief` caps the list at
  25 now, and an explicit `--limit N` is obeyed as given.

- The report answers the directory before it answers a file. It used to open on
  its first entry, which is the seventh question an analyst asks; the six that
  come first now have sections of their own. A masthead saying what was scanned
  and how much of it answered, an `inventory` of every type present with its
  share of the files and the bytes, a `findings` table naming what was found, and
  an `attention` block for the few things a long report otherwise buries. A scan
  of a single file skips all four - there is nothing to inventory but itself.

- Three names that described the model rather than the contents. The masthead
  said `73 of 105 traced` over a count of files carrying any origin at all: a
  PDF with an Info dictionary has not been traced anywhere, it has described
  itself, and the closing line repeated the same number as `have a recorded
  origin`. Both now count files, findings and silence separately. The
  self-reported section is headed `file metadata` rather than `claimed by the
  file itself`, and the list at the end is `no findings` rather than `no recorded
  origin` - which named a narrower case than the list has ever held, since a file
  is in it only when nothing at all was found. Each claim inside still reads
  `self-reported` beside its own source, so no methodological care is lost.

- The reader table moved to the end, under `metadata sources`. It answers which
  readers produced results, which is a technical question and was standing in
  for what was actually found.

- The landing screen is twenty-four lines instead of forty. It says what the
  tool is for in three - metadata, provenance, analysis - then six ways in, the
  command names, and where the rest is. The option table it used to reprint is
  in `filegrail help <command>`, which is where somebody looking for an option
  goes anyway. The tagline says both halves of the job.

- Every claim records which metadata block it was decoded from, beside the
  source it already carried. The two answer different questions. `source` names
  what the reader *found* - `device-metadata` where a file named a camera,
  `document-metadata` where it did not - and is what confidence, colour and
  kind turn on. `block` names what it *read*: `pdf-info`, `png-text`, `exif`,
  `ole-summary`, `iptc`, `xmp`. It appears in `--json` as `block`, and a record
  that decoded no metadata block does not have one.

  Nine readers answer to `document-metadata`, which is why the distinction had
  to exist before a PDF pairing could. Keyed on the source, the EXIF mirror
  reached all nine: a WAV's `INFO` list has a field spelled Software, and beside
  an XMP packet the tool reported `Software: RIFF INFO says Audacity 3.4.2, XMP
  says Adobe Audition 24.0` - a contested attribution between a RIFF field and a
  TIFF tag, invented out of two standards sharing a word. `Mirror.left` and
  `Mirror.right` now name blocks, and `left` is a plain string rather than a
  tuple of source names.

- The conclusion no longer ranks two blocks it has no basis to rank. IIM and a
  camera's EXIF tags go stale because an editor rewrites the XMP and copies them
  through untouched, and the sentence said so. A PDF has no such direction: one
  producer writes both blocks, and an exporter stamps a fresh Info dictionary
  while carrying the XMP through from the source document - the corpus file has
  XMP from February beside an Info dictionary from May, so naming the Info as
  the likelier to be stale would have stated the opposite of what happened.
  A pairing now carries which of its two sides an editor keeps current, or that
  it has no answer, and the conclusion follows it. `--json` carries it too, as
  `maintained` on a finding that has one.

- A claim is named by its block where the source would only say `document
  metadata`. That label names a category rather than a thing, and the summary
  collapsed a whole corpus into one line reading `document metadata 39` when it
  could say which nineteen were OOXML properties and which six were PDF Info.
  Every other source keeps its own name: `device metadata` says the block held a
  make and a model, which is why it outranks a bare document property, and
  `EXIF` would throw that away.

- The WAV and AVI block is `riff` rather than `riff-info`. That reader decodes
  three chunk families and already names every field for the standard it came
  from - `bext:Originator` beside `id3:encoder` beside a plain INFO field - so
  the block only had to name where they were all found. It named one of the
  three instead, and a broadcast recording carrying no INFO list at all was
  reported under the label of the chunk it did not have. `matroska` and
  `isobmff` are named for their containers for the same reason.

- Two timestamps are compared as instants where both writers said what zone they
  were in, and as readings where either did not. The zone used to be dropped
  outright, which EXIF requires - it writes no zone at all while its XMP mirror
  writes the same reading with one attached - but a PDF carries an offset in
  both of its blocks, and one machine varies it across the year. The corpus has
  an export whose Info dictionary says `-04'00'` where its XMP says `-05:00`,
  the same laptop either side of a daylight change; comparing the readings would
  have reported a single moment as a contested attribution.

- Modes are commands now, not flags: `filegrail explain FILE`,
  `filegrail compare A B`, `filegrail doctor`, `filegrail menu`,
  `filegrail help <command>`. `--doctor` and `--explain` were modes wearing an
  option's clothes - each ignored most of the other options, and every pair of
  them was mutually exclusive, which is exactly the shape subcommands exist to
  express. `filegrail <path>` still scans with no command word, because that is
  what people do most of the time and making them type `scan` would be ceremony.
- `-v`, `-j` and `-h` short forms. The evidence-source table moved off the
  landing screen into `doctor`, where the question has actually been asked;
  what the screen says instead is described above.

### Fixed

- Metadata field names are names. A packet whose namespace the prefix table had
  never listed printed the URI instead, four times over inside one name:
  `xmpMM:History/http://www.w3.org/1999/02/22-rdf-syntax-ns#:Seq/...:li/stEvt:action`.
  RDF's own namespace was the worst of them, and this file had been defining it
  two lines above the table since the reader was written; `xmpG`, `xml` and
  `pdfuaid` were missing too.

  The array wrappers went with them. `rdf:Seq` and `rdf:li` are how RDF spells
  "several of these" and say nothing about the property, so they are no longer
  path segments - a swatch group is `xmpTPg:SwatchGroups/xmpG:groupName`, and
  several of them are numbered rather than dropped on each other's name, which
  is what `setdefault` had been doing in silence. One corpus PDF carries
  Illustrator's entire default palette, so an array reports its first three
  entries and states how many there were, the way the edit history already
  bounds itself.

  The edit history is no longer flattened into the fields at all. Every step is
  already its own dated claim with its own `stEvt:` fields, and walking the
  sequence a second time printed each of them twice.

  `--json` carries the corrected names. The document's shape is unchanged and no
  field changed meaning, so the schema number stands: what moved is the reader's
  own naming of things inside an open dictionary, and the names it moved from
  were not usable.

- Field names, file names, identifiers and scanned paths wrap instead of being
  cut. `DESIGN.md` has said nothing is truncated since the first release, and
  four XMP fields were printing as `xmpMM:DerivedFrom/stRef…` - four rows nobody
  could tell apart, over four values nobody could attribute to a field. A name
  too wide for its column now takes a line of its own and its value follows
  underneath. `--timeline` was cutting names and claims for the same reason.

- The identifiers section is ASCII on a terminal that cannot print a middot. The
  separator inside a place string was written once and printed as written.

### Added

- `--home DIR` reads the browser, shell and desktop history of another user
  profile instead of the current one, on `scan`, `explain`, `compare` and
  `doctor`. `scan()` and `survey()` had taken a home directory as an argument
  since they were written; nothing offered it on the command line, so the
  answer was always about the machine doing the asking - which is the wrong
  machine whenever the interesting one is a mounted image or a copied profile.

  It works across platforms without porting, because the profile locations for
  Linux, macOS and Windows were already in one list and searched under whatever
  home is given. A Windows Chrome profile read from Linux resolves.

  Two things change when the traces are not this machine's, and both are things
  the report would otherwise have got wrong. `this machine` becomes `that
  machine` and the report names the profile it read - on paper a foreign-profile
  report was previously indistinguishable from a local one. And when there is no
  acquisition record, the advice to run `doctor` now carries the same `--home`,
  because sending a reader to survey their own laptop about somebody else's
  profile wastes the one step that would have told them the truth.

  A `--home` that does not exist is refused rather than searched. Every source
  would come back empty, and a run that found nothing because it looked in the
  wrong place is indistinguishable from one that found nothing because there was
  nothing to find - which is the exact confusion `doctor` exists to prevent.

- Every `--json` document now begins with what it is: a `schema` naming the
  shape, and a `filegrail_version` naming the build that wrote it. The four
  shapes are `filegrail.scan/1`, `filegrail.explain/1`, `filegrail.compare/1`
  and `filegrail.doctor/1`.

  `--json` is a contract with software, not a convenience for reading, and it
  had no way to say which contract. Something switching on the keys it found
  would break silently the first time a field was renamed, in a program nobody
  here can see. The stamp is also the kind of thing that can only be added for
  free once: adding a key is itself a change for anyone who enumerates them, so
  the cheapest moment to do it is before there are consumers. The schema number
  moves only when a field changes meaning or leaves - a new field is not a
  break, and neither is a release, which is why the two live in separate keys.

  `explain` and `compare` built their JSON inline in the command layer, so
  there were four documents defined in two files. All four are now rendered in
  `report.py` through one function, which is what makes the stamp a single
  decision rather than four.

- Reconciliation now compares a PDF's `Info` dictionary against its XMP, and a
  PNG's text chunks against theirs. Both pairings are published in Part 3 of the
  XMP specification, alongside the IIM and EXIF ones already checked: the Info
  entries are the legacy form of `dc:title`, `dc:creator`, `dc:description`,
  `pdf:Keywords` and `xmp:CreatorTool`, and the standard PNG keywords map the
  same way.

  One producer writes both of a PDF's blocks at one save, so agreement is the
  ordinary case and worth no line. A difference is the trace of an export that
  stamped a fresh Info dictionary over XMP carried through from the source
  document. On the developer's corpus this finds an InDesign export whose Info
  names InDesign where its XMP still names the Illustrator document behind it,
  three months earlier - and a Writer export whose title and creation date
  belong to a thirteen-year-old file.

  `/Producer` is left out. It names the library that wrote both blocks, so it
  disagrees with itself rather than with anything: Adobe PDF Library 15 puts
  `Adobe PDF Library 15.0` in the Info dictionary and `Adobe PDF library 15.00`
  in the XMP. `/Trapped` is left out because it is a PDF name object rather than
  a string, and the reader takes only string values.

  The PNG pairing is spec-only. No file in the corpus carries both a text chunk
  and an XMP packet, so it has been read against synthetic files alone. Its
  `Creation Time` is compared where it can be read; the specification asks for
  RFC 1123, which nothing here parses, and an unreadable stamp is skipped rather
  than reported.

  Reading a PDF's dates needed the moment comparison taught the form a PDF
  writes. `D:20180511143720-04'00'` opens with two letters the day pattern would
  not match past and runs the clock straight into the day with none of the
  separators the clock pattern looked for, so every PDF timestamp came back
  unreadable - and an unreadable stamp is never compared. They were being
  skipped in silence.
- Saved messages, read for how they travelled. `Received:` headers are the only
  part of an email not written by the sender: each mail server prepends its own
  as the message passes through, so they read from the bottom up. Each hop
  becomes an event of its own, the way a recorded XMP edit does, so the whole
  chain lands on `--timeline` in order.

  They are not ranked alike, because they are not worth the same. The topmost
  was written by the recipient's own server and nobody else could have forged
  it; it goes in at 78, below the attributes an operating system keeps outside
  the file and above an archive's inheritance. Every hop under it was written by
  a machine the sender may control, and those go in at 45. What the message says
  about itself - who it is from, what the subject was, which client composed it
  - is a self-description checked by nobody and goes in at 30, the weakest in
  the table, because forging a `From` line takes nothing but typing it.

  The address each server actually saw is kept beside the name the connecting
  host claimed for itself, and both reach `--identify` along with the addresses
  and domains in the headers. A message id does not: RFC 5322 builds one to the
  same shape as a mailbox, so it matches every test for an address and nobody
  can write to it. Its domain is still reported - that names the host that
  minted it, which is a real fact about where the message was written.

  `.eml` only. An mbox holds many messages and one record per file has no honest
  way to describe them all; `.msg` keeps its headers as MAPI properties inside a
  compound document, which is a different reader. Both are left for their own
  design rather than half-answered here.

- Vorbis comments, which FLAC, Ogg Vorbis and Opus all carry: one layout in
  three containers. FLAC keeps the block among the metadata blocks at the front
  of the file and those can be walked exactly; Ogg keeps it in the second packet
  and it is found by the marker that opens it, rather than by reassembling Ogg
  pages for a block that has already been located. The cost of that shortcut is
  named where it lands: a comment block long enough to be split across pages
  stops being readable partway, so every length is checked against what was
  actually read and whatever was recovered is returned as it stands.

  The names are case-insensitive by specification, and ffmpeg takes it at its
  word - every field it writes is in lower case. The first draft looked them up
  shouted and so found nothing at all in the files ffmpeg produces, which is a
  reader agreeing with the specification and disagreeing with reality. They are
  looked up without regard to case now and kept in the record exactly as the
  writer wrote them; shouting a studio's own field names back at it is editing
  the evidence.

  Cover art arrives base64-encoded in a comment like any other and is left out.
  It is not provenance, and a screenful of it would bury the handful of values
  that are.

- Matroska and WebM, read through EBML. `.mkv` and `.webm` were already
  selectable with `--type video` and no reader claimed them, so a scan narrowed
  to the films read nothing out of them. The container names the application a
  person used and the library that muxed the file, and those are only reported
  separately when they differ - ffmpeg writes its own name into both, and
  "Lavf60.16.100 (muxed with Lavf60.16.100)" is a sentence about nothing.

  The tag block is open by design: a muxer puts anything there the format has no
  field for, under whatever name it likes. Those names are kept as written,
  because a reader that knows only a fixed list throws away the ones that
  mattered.

  Matroska counts its segment date in nanoseconds from the start of 2001, not
  from 1970. Read as a Unix time it puts every file made this century
  thirty-one years early, which is wrong in a way that looks plausible enough to
  go unnoticed. The field is also signed, so a muxer handed a wrong clock has
  what it wrote read back rather than turned into the year 586.

  A segment can decline to state its own length - a muxer writing to a pipe does
  not know it - and then it runs to the end of its parent. `ffmpeg -f webm
  pipe:1` writes exactly that, and the first draft of this reader returned
  nothing at all for such a file. Only a master element may do it; a leaf that
  tries is refused, because there the value would be however much of the file
  happened to follow.

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

- The tagline says both halves of what the tool does: `trace origins, extract
  metadata`. It said only the first, and the landing screen it sits on had ten
  examples without one that mentioned metadata - including `filegrail
  suspicious.pdf`, the command that prints the whole field tree, described as
  `one file`. The capability now sits in the examples, where a reader looks for
  capabilities, rather than in a second slogan under the first.

  Four characters longer than the line it replaces, because `where files came
  from` spent five words on one idea and the wordmark says `filegrail` directly
  above it. The banner, both READMEs and the `aria-label` say the same thing.

  `--home` and `--timeline` are in the options list. `--home` is the newest
  thing the tool can do and was on the screen nowhere.

- Timestamps print to the second. GTK writes microseconds into
  `recently-used.xbel` and a shortcut carries the filesystem's own precision, so
  a claim from either sat beside a dozen stamps that stop at the second and read
  as an inconsistency rather than as precision. `--json` still carries every
  digit, and `--timeline` already did this.

- `explain` puts a blank line under the rule before naming the profile it read,
  the way the scan report does.

- The README is rewritten around what the tool does rather than around how its
  evidence model works. `What filegrail does` opens with metadata extraction and
  provenance reconstruction as two named capabilities; `Metadata analysis` is a
  section of its own rather than a table two thirds of the way down; the
  contents list and the per-section back-links are gone, and the anchors that
  remain are the six a reader actually jumps to.

  Some reference material moved out rather than being reworded: the confidence
  table, the four reconciliation pairings, the `source` and `block` fields in
  `--json`, and the spec-only readers. [`FORMATS.md`](docs/FORMATS.md) carries the
  format and block detail; the rest is in `CHANGELOG.md` and `DESIGN.md`.

- The README says what it can read before it says how it ranks it. The metadata
  half was one item in a list of seven in the opening paragraph, which is a
  strange way to describe the substance of the tool - `CONTRIBUTING.md` calls it
  exactly that. It now has its own sentence, with the count and a link, and the
  `Supported metadata` section opens with the scale rather than with a note
  about output formatting. macOS quarantine was missing from the list of traces
  entirely.

  The JSON section said nine readers answer to `document-metadata`. That was
  true before three more were added; fifteen blocks can carry it now, which is
  every block there is.

- [`FORMATS.md`](docs/FORMATS.md): the complete list of what can be read out of a
  file, with the metadata block each format produces, what is deliberately not
  read, and which three readers are written from a specification rather than
  tested against files the originating software wrote.

  It lives outside the README because it is the one table guaranteed to grow -
  `CONTRIBUTING.md` asks for new readers, and a README that swells with every
  one of them rots. And because out here it can be held against the code:
  `tests/test_documented_formats.py` parses the tables and compares them with
  what the readers actually declare, in both directions. A format that is read
  and undocumented fails, and so does one documented that nothing reads.

  That makes it the first document in this repository that cannot quietly stop
  being true. A list of formats in prose is otherwise the kind of documentation
  most certain to rot: every new reader is a line somebody has to remember, and
  nothing notices when they do not.

- The Windows Recent folder is read. A `.lnk` under
  `AppData/Roaming/Microsoft/Windows/Recent` is the counterpart of a
  `recently-used.xbel` entry and is ranked with it: opening a file proves
  contact, not acquisition, and this does not pretend otherwise.

  What a shortcut adds is *where the file was when it was opened*. It records
  the volume by type, serial number and label, a network share by name, and -
  where the tracker block survives - the NetBIOS name of the machine that
  created the link. That supports a statement nothing else here could make:
  this file was opened from a removable volume, or from an optical disc, or
  from `\\fileserver\projects`. It remains a fact about handling rather than
  about arrival, however suggestive it reads, and it is filed as one.

  The shortcut also records the size and last-write time of what it pointed at,
  so a name match can be corroborated the way a download record's is. The
  recorded path is a Windows one and is split as such, which is the fix from
  earlier in these notes doing its work a second time.

  Spec-only in one direction: nothing available writes a `.lnk`, so the
  fixtures are assembled from [MS-SHLLINK]. The folder walk and the matching
  around it are ordinary.

- macOS quarantine is read: the `com.apple.quarantine` attribute on the file,
  and the LaunchServices `QuarantineEventsV2` database under the user's home.
  The attribute names the application, the moment and an event identifier; the
  database says what that identifier stands for - the URL the bytes came from
  and the page that linked to it.

  They are two halves of one record rather than two witnesses, so they are
  reported as one claim. Emitting both would read as corroboration, and a
  subsystem agreeing with itself corroborates nothing.

  Two epochs, which is the trap in the format. The attribute counts seconds
  from 1970 and writes them in hexadecimal; the database counts them from 2001,
  the way every Core Foundation timestamp does. Reading either with the other's
  epoch puts the download decades from where it happened.

  The database is what makes this worth having away from a Mac. It sits under
  the home directory, so `--home` reaches it from anywhere - and since a file
  copied out of an image rarely keeps its extended attributes, a row whose
  recorded URL ends in the file's name is matched that way, marked as a name
  match like any other.

  `matched_by_name` now takes the reason a name was all there was. A download
  record keeps the path the file was saved to, so a name match there really
  does mean it moved; a quarantine row keeps no path at all, and saying it
  moved would describe a disagreement between two things where only one of them
  exists.

- A saved Outlook message is read for how it travelled. `.msg` was already
  opened as a compound document, because its Office-style summary properties
  sit where a `.doc`'s do; what was never read is
  `PR_TRANSPORT_MESSAGE_HEADERS`, the stream holding the internet headers. That
  block is the same RFC 5322 text an `.eml` starts with, so it goes through the
  same parser and yields the same `Received:` chain - the one part of a message
  the sender did not write. Both spellings of the property are asked for, UTF-16
  and 8-bit, because which one a message carries depends on the sender's Outlook
  and not on anything in the message.

  A message delivered inside one Exchange organisation never crosses the
  internet and has no such headers. No delivery record is invented for it; what
  it says about itself - subject, sender, message id - is reported as exactly
  that, from the MAPI properties, and only where the headers are absent, since
  a header block already carries its own.

  Spec-only. Nothing on the developer's machine writes a `.msg`, so every
  fixture is assembled from [MS-OXMSG] and the reader has never been run
  against a file Outlook produced. The container walk underneath it is not:
  that is the same one the corpus exercises through real `.doc` files, now
  exposed as `read_streams` so a reader of a compound document that is not an
  Office one does not have to walk a FAT of its own.

- `doctor` reports the desktop's list of recently opened files, and how far
  back the shell history and that list reach. It surveyed browsers, the
  operating system's origin attribute, the shell, creation timestamps and C2PA
  - but not `recently-used.xbel`, which a scan reads on every run. The file
  opens by promising to say up front what could be searched, and a reader could
  be handed a finding from a source the survey had never mentioned. An
  incomplete promise of that kind is worse than none, because nothing tells the
  reader where the gap is.

  `HOME_SOURCES` now names every source that reads a home directory beside the
  checks that report it, and a test holds it against `sources` itself, so the
  next collector added without a check fails rather than going unreported.

  The note under the horizon said a file older than it cannot be resolved from
  browser history. With a shell and a desktop list beside them it was
  describing one row of three, and reading as though the other two carried no
  limit at all.

### Fixed

- An ODF document reported three fields where it carried eight, and two of the
  three were invented. `meta:user-defined` is a list of arbitrary document
  properties whose names live in an attribute rather than in the tag, and it was
  read like every other child element: the first value won, the rest were
  dropped, and the attribute names of the others scattered into fields of their
  own. The corpus spreadsheet came back saying `user-defined 16.0300`, `name
  AppVersion` and `value-type float` - three lines, none of which anybody wrote,
  in place of six properties.

  They are now keyed on the name the document gave them, and collected apart so
  that a real element always wins: a user-defined property may legitimately be
  called `creator`, and it does not get to answer for `dc:creator`.

  Attributes are still read from every other child, because the statistics
  element keeps its page, table and word counts in them and nowhere else. That
  was the reason the rule existed; `user-defined` was the case it did not fit.

- The macOS where-from attribute could never be read on macOS. `os.getxattr`
  is a Linux interface - the standard library does not expose the call on macOS
  at all - and every reader here guarded on `hasattr(os, "getxattr")`, so on
  the one platform `kMDItemWhereFroms` exists, the reader that exists for it
  did nothing. `doctor` said so, which is why this survived: it reported the
  source as unavailable there and was believed.

  Attributes now go through `util.read_xattr`, which calls libc on macOS the
  same way creation timestamps already do. macOS takes two arguments the Linux
  call does not, a position and a flags word, which is why one interface does
  not cover both. The tests write an attribute the same way, so the macOS path
  is exercised on a macOS runner rather than reasoned about.

  The macOS attribute is also read under the `user.` namespace, which is where
  a copy carries it onto a system with no other namespace to put it in - the
  same reason the quarantine attribute is read under both names.

- `doctor` counts in the singular where there is one of something. Four checks
  wrote `1 records`, `1 files`, `1 downloads` and `1 shortcuts`, which is the
  kind of seam that makes a report look assembled rather than written.

- A download record written by another operating system never matched by name.
  `Path` knows only the separator of the machine reading it, so
  `C:\Users\Alice\Downloads\evidence.zip` split with `PosixPath` has no
  directory at all and its whole spelling comes back as the file name. Every
  Windows record read from Linux or macOS therefore failed to match silently.

  Names are now taken with `util.basename`, which treats a backslash as a
  separator only where the path announces itself as a Windows one - a drive
  letter or a UNC prefix - because a backslash is a legal character in a POSIX
  file name and mangling those would trade one silent failure for another.

  The bug was invisible before `--home` because a record and the file it
  described came from the same machine, so both were spelled the same way.

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

- `filegrail compare A B`: what two files record about themselves that agrees,
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
- A landing screen. `filegrail` with no arguments now introduces itself - name,
  version, author, repository, licence, worked examples and the sources it reads
  with their confidences - instead of silently scanning the current directory.
  Starting an unasked-for scan of wherever the shell happens to be is a surprise,
  and in a home directory an expensive one; the screen says `filegrail .` for the
  folder you are standing in. `--about` prints it again from anywhere. Nothing on
  it waits for input, so it works piped and in a script.
- An interactive front end, `filegrail --menu`, for choosing a view without
  memorising flags. It is printed text and `input()` rather than curses, so it
  keeps the zero-dependency promise and works over SSH and on Windows. It
  refuses to start when output is redirected, and it prints the `filegrail`
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
  [`DESIGN.md`](docs/DESIGN.md) so it can be argued with. Entries are bound together
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
- Renamed the project to `filegrail`. The previous name was crowded on GitHub,
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
