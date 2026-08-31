# Changelog

All notable changes to `filetrail` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
the project uses [semantic versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

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
