# Evidence — filetrail TUI Design System

> A forensic report that happens to live in a terminal. Quiet, dense, and
> honest about how much it knows.

Written to the [awesome-tui-design](https://github.com/cola-runner/awesome-tui-design)
`TEMPLATE.md` structure. Every value here is what `src/filetrail/theme.py`
actually emits — this is a description of the implementation, not an aspiration.

## 1. Theme Overview

- **Mood**: Forensic, quiet, precise. A lab notebook, not a dashboard.
- **Density**: Balanced. Entries are multi-line and grouped; whitespace does the
  separating so no box has to.
- **Target**: A non-interactive report. It prints once, scrolls past, and is
  frequently pasted into a case file — so it must read as well in a text editor
  as on a terminal.
- **Terminal**: 16-colour minimum, 256 preferred, TrueColor used when offered.

### The order of the answers

A report is read from the directory down to the file, never the other way. The
sections come in the order an analyst asks for them:

1. **Scan overview** — what was scanned, how much of it, how much of it answered
2. **Inventory** — every type present, with its share of the files and the bytes
3. **Findings** — what was found, named for what it is
4. **Attention** — the few things a long report would otherwise bury
5. **Entries** — one file at a time, grouped by evidence class
6. **No findings** — the files nothing was found for
7. **Metadata sources** — which readers produced results, which is a technical
   question and belongs after the evidence rather than in front of it

The first four are skipped for a scan of a single file. There is nothing to
inventory but itself, and a findings table over one file is ceremony in front of
the answer.

### Two questions, never ranked against each other

A file can answer two different questions, and the report keeps them apart:

| | asks | answered by |
|---|---|---|
| **Acquisition** | how did this get onto this machine | browser downloads, OS origin attributes, archive membership, shell history, filesystem times |
| **Intrinsic** | what does it say about its own earlier life | EXIF, document metadata, C2PA |

Both are printed, acquisition first. Ranking them against each other by
confidence looks reasonable and is wrong: a download record scores higher than a
camera's EXIF, so a geotagged photograph that had been downloaded reported its
URL and no GPS at all. The stronger claim was deleting the more valuable one.

### The one idea

**Colour encodes how the tool knows, never what it found.** A green line was
recorded by some other system. A blue line is the file talking about itself. The
reader learns five colours once and can then triage a folder without reading a
word. Nothing else in the interface is allowed to use colour.

## 2. Color Palette

### Semantic Roles

| Role | Hex | ANSI 256 | ANSI 16 | Usage |
|------|-----|----------|---------|-------|
| Background | terminal default | — | — | Never painted; the user's choice wins |
| Foreground | `#d0d0d0` | `252` | `white` | File names, body text |
| Muted | `#8a8a8a` | `245` | `bright black` | Labels, source names, counts |
| Faint | `#585858` | `240` | `bright black` | Rules, rails, timestamps, empty meter |
| Warning | `#d7875f` | `173` | `yellow` | Interrupted downloads, contested claims |

### Evidence Classes

The load-bearing part of the palette. Each class answers "who is making this
claim", and its colour is used for the entry bullet, the origin line and the
confidence meter of every origin in that class.

| Class | Sources | Hex | 256 | 16 | Reads as |
|-------|---------|-----|-----|----|----------|
| Recorded | `browser-download`, `windows-zone-identifier`, `macos-wherefroms`, `xdg-xattr` | `#5faf87` | `71` | `green` | Another system wrote this down at the time |
| Inherited | `archive-member` | `#5fafaf` | `73` | `cyan` | Carried over from the archive it came out of |
| Credentialed | `c2pa` | `#af87af` | `139` | `magenta` | A provenance manifest, signature unverified |
| Self-reported | `device-metadata`, `document-metadata`, `xmp`, `xmp-history`, `iptc` | `#5f87af` | `68` | `blue` | The file's own account of itself |
| Circumstantial | `shell-history` | `#d7af5f` | `179` | `yellow` | A command mentioned the name; proves contact, not creation |
| None | `filesystem`, no origin | `#585858` | `240` | `bright black` | Nothing accounts for it |

Ordering is deliberate: the table reads top to bottom from strongest to weakest,
and so does the report.

### Neutral Scale

| Step | Hex | 256 | Usage |
|------|-----|-----|-------|
| 100 | `#3a3a3a` | `237` | Rails between an entry's lines |
| 200 | `#585858` | `240` | Rules, timestamps, empty meter slots |
| 400 | `#8a8a8a` | `245` | Labels, secondary text |
| 500 | `#d0d0d0` | `252` | Body text, file names |

### Depth Fallback

Resolved once, at startup, from `COLORTERM` and `TERM`:

`truecolor` → `256` → `16` → none. A terminal that cannot colour gets the same
layout in plain text, never a different one.

## 2b. The mark

The logo is not decoration bolted on afterwards; it is this palette, drawn.

Five slots of the confidence meter, laid on their side so their left ends form
the `←` the report uses to mean *came from*. The bars carry the evidence classes
in table order, top to bottom: recorded `#5faf87`, inherited `#5fafaf`,
credentialed `#af87af`, self-reported `#5f87af`, circumstantial `#d7af5f`.

**Do not recolour, reorder or reweight the bars.** Their order is the evidence
hierarchy, and changing it makes the mark say something the tool does not.

| File | Use |
| --- | --- |
| `assets/filetrail-banner.svg` | 1280×360 README header |
| `assets/filetrail-logo-dark.svg` | horizontal lockup, dark backgrounds |
| `assets/filetrail-logo-light.svg` | horizontal lockup, light backgrounds |
| `assets/filetrail-mark.svg` | square mark, dark backgrounds and favicon |
| `assets/filetrail-mark-light.svg` | square mark, light backgrounds |
| `assets/filetrail-mark-mono.svg` | single colour, for one-colour contexts |

Light-background variants darken the same five hues for contrast on white; the
monochrome variant uses Foreground `#d0d0d0`. Clear space is one bar-height - 6
units on the 64-unit grid - on every side. The wordmark is any monospace at
weight 700, letter-spacing -2%, always lowercase.

## 3. Typography & ASCII Art

- **Header font**: None. No figlet, no banner. A report does not introduce itself.
- **Emphasis**: `bold` only. No italic, no underline, no reverse video.
- **Values**: never coloured for emphasis — colour is reserved for evidence class.

### Text Hierarchy

| Level | Style | Usage |
|-------|-------|-------|
| H1 | BOLD Foreground + Faint path | The masthead line |
| H2 | Muted, lowercase, followed by a rule | Evidence-class section headers |
| Body | BOLD Foreground | File names |
| Claim | Evidence-class colour | The origin line, after `←` |
| Label | Faint, padded to 10 columns | `geo`, `location`, `referrer`, `note`, `from` |
| Caption | Faint | Timestamps, sizes, counts |

Section headers are lowercase on purpose. Capitals read as chrome; this report
has no chrome.

## 4. Borders & Box Drawing

**There are no boxes.** Nothing in a provenance report needs to be in a frame,
and a frame costs two columns of width on every line it wraps.

Grouping is done with a one-character left gutter instead.

### The Gutter

Every line of an entry begins at column 2 with exactly one glyph, so the left
edge of the report is a single readable column:

| Glyph | ASCII | Meaning |
|-------|-------|---------|
| `●` | `*` | This is a file. Painted in its evidence class. |
| `←` | `<-` | This is where it came from. Painted in its evidence class. |
| `│` | `\|` | A continuation of the claim above. Always Faint. |
| `├` | `+` | One decoded field. Always Faint. |
| `└` | `\\` | The last decoded field. Always Faint. |

Every glyph is padded to the width of the widest, because the ASCII arrow is two
characters and a gutter that is not one column is not a gutter.

## Nothing is truncated

A value too long for the line **wraps**; it never ends in an ellipsis. A report
exists to be read, and a cut-off value is one the reader now has to fetch another
way, which defeats having read the file at all. Words stay whole where they fit;
a single token longer than the line - a URL, a hash - is split, because the
alternative is a line that overflows the terminal.

**The names of things are data too.** A field name, a file name, an identifier
and a scanned path all wrap on the same rule as a value. A field name cut to
`xmpMM:DerivedFrom/stRef…` leaves four rows nobody can tell apart and four values
nobody can attribute to a field; half a path still looks like a path. A name too
wide for its column takes lines of its own, and the value follows underneath it:

```
  ├ xmpMM:DerivedFrom/stRef:documentID
  │                         xmp.did:dac92226-1901-469c-9e41-22f9d830ec3a
```

The one exception is navigational chrome — the landing screen, where a gloss
beside a command may give way on a narrow terminal. Nothing in the analytic
material of a report is ever abbreviated.

Every field a reader decoded is printed **by default**, as a tree hanging off the
claim it belongs to. `--brief` collapses it. A reader who has to run the command
a second time to see what the tool already knew has been told less than it knew.

```
  ● invoice-scan.pdf                                              1.2 MB
  ← https://portal.example.org/billing/2026/invoice-scan.pdf
  │ browser download · firefox · 2026-08-24T19:02:11Z        ▰▰▰▰▱ 90
  │ referrer  https://portal.example.org/billing
```

Three glyphs, one meaning each, one column. Under `--verbose` a second `←`
starts the next claim on the same file, and the gutter still parses.

### Dividers

- Section rule: `─` to the full width, in Faint. Used under the masthead and
  under each section header. Nowhere else.
- No vertical dividers. No section-break ornaments.

## 5. Components

### Two headers, one mark

The wordmark appears in two places and says a different amount in each.

**Start screen** — the front door. Wordmark, repository, licence, version,
tagline, the three areas the tool covers, usage, six ways in, the command names,
and where the rest of the help is. Its job is to get somebody to a first command.

**Report banner** — the letterhead. Wordmark, version, tagline, target, scan
statistics. Nothing else: a report is not an introduction, and a reader holding
one already knows what they ran.

```
    __ _ _     _           _ _
   / _(_) |___| |_ _ _ __ _(_) |
  |  _| | / -_)  _| '_/ _` | | |   filetrail 0.1.0
  |_| |_|_\___|\__|_| \__,_|_|_|

  Trace where files came from. Extract what they reveal.

  target    /data/case-files
  scanned   105 files · 32 types · 19.8 MB
  findings  73 files · 32 without findings

  ────────────────────────────────────────────────────────────────────────
```

A report is redirected to a file more often than it is read on screen, and a
`report.txt` that does not say what produced it is a wall of text somebody has
to identify from memory. Below 52 columns the version drops to its own line
under the mark; the target wraps rather than clips, like every path here.

The scale and the yield are separate rows because they answer separate
questions. It used to read `73 of 105 traced` over a count of files carrying any
origin at all — a PDF with an Info dictionary has not been traced anywhere, it
has described itself, so the word claimed something the tool does not know.
Nothing outside the acquisition sections is called a trace.

### Inventory

```
  inventory                                                      33 types
  ────────────────────────────────────────────────────────────────────────

    JPG   20    3.6 MB    PDF   18    3.4 MB    DOCX   9  200.2 KB
    PNG    6    2.8 MB    XLSX   6  143.7 KB    PPTX   5  258.9 KB

    image  37    video  2    document  45    text  14    other  5
```

Every extension present, with how many files and how many bytes, then the same
files by family. No top ten and no `…`: which types are in a directory you did
not assemble is the first thing worth knowing, and a list that stops at the tenth
answers it for the part you had already guessed.

The families are the ones `--type` already filters on, read from the same table,
so a name in the inventory is a word you can type. A file belongs to exactly one
of them, by a fixed precedence, so the counts add up to the total.

**Formats, not extensions.** `JPG 20` beside `JPEG 1` counts one format twice,
so the obvious spellings fold to the name the format is usually called by —
`jpg`/`jpe` → `JPEG`, `tif` → `TIFF`, `yml` → `YAML`, `htm` → `HTML` — and a
compressed tarball is `TAR.GZ` rather than `GZ`, which said nothing the file name
had not. Presentation only: `--type`, `--ext`, the record and the JSON keep the
extension the filesystem has, and folding a name never moves a file out of the
family `--type` would select.

Columns are laid out to the terminal: four, three, two, one, as it narrows. The
cells never shrink. **Give up a column before giving up a digit.**

### Findings

```
  findings
  ────────────────────────────────────────────────────────────────────────

    creating software     66 files
    device information    18 files
    content credentials    1 file
    coordinates            8 files
    conflicting evidence   3 files
```

What was found, named for what it is rather than for the reader that found it.
A row nothing matched is left out rather than printed as a zero — a column of
zeroes reads as a list of the things the tool cannot do.

**Two rows are printed even at zero**: `metadata` and `acquisition evidence`.
The tool stands on those two things, and a scan that read a great deal of the
first and none of the second has *found that out*. Leaving the row off would make
an answer look like an omission.

Units say what they count. `73 files` is files; `15 unique identifiers` is
identifiers, because one address across forty files is one lead. Labels are the
words an analyst uses rather than the model's — `timestamps`, not `dated claims`.

`authors / creators` is keyed on the block, not on the field name. `Creator` is
the application in a PDF Info dictionary and the person in OOXML core
properties; one flat list of names would count every PDF's typesetter as its
author. Every block is either given an author field or declared to have none,
and a test holds both lists against the readers.

The digits are aligned, not the phrases: `1 file` and `66 files` right-aligned
whole puts the 1 under the s of files, which is a column of nothing.

How many files said anything at all is not a row here. The masthead counts it,
and a second number under a slightly different name is a second number to keep
in agreement with the first.

### Notable Findings

```
  notable findings
  ────────────────────────────────────────────────────────────────────────

  ! 3 files contain conflicting evidence
  │   Investigative_Case_File_Review_Final.pdf
  │   OSINT360 Target Architecture v0.3.pdf
    8 files contain coordinates
    1 file contains Content Credentials
    15 unique identifiers extracted
```

Printed **only when there is something in it**. Not an alarm panel: coordinates
and Content Credentials are findings, not problems, which is why the heading is
`notable findings` and not `attention`.

`!` is the only glyph here, and only for evidence that disagrees with itself.
**`●` is not used.** It means *this is a file* everywhere else in the report, and
a count line is not a file; spending it here would cost the gutter the one
symbol it has for that. The remaining rows are indented to the same column and
left unmarked.

A conflict names the files behind it, up to five, and then says how many more
there were and that each is marked below — a capped list that does not admit it
reads as the whole list.

No colour is spent beyond Warning on the contested line, which is the one thing
in the palette that already means *this disagrees*. These lines are counts, not
claims, and painting a count by how alarming it is is the one thing this
interface never does with colour.

### Section Header

```
  file metadata                                                 72 files
  ────────────────────────────────────────────────────────────────────────
```

Printed **only when more than one class is present**. A folder whose files all
resolve the same way gets no headers at all — the grouping would be noise.

The self-reported class is headed `file metadata`. It used to read `claimed by
the file itself`, which is true, methodologically careful, and says nothing about
what is in the section. Nothing is lost by the change: every claim inside still
carries its own source and reads `▰▰▱▱▱ self-reported` beside it.

### Entry

See The Gutter above. Size is right-aligned on the name line; the confidence
meter is right-aligned on the source line. Two right-aligned columns, never on
the same line, so neither has to compete for width.

### Confidence Meter

```
▰▰▰▰▱ 90        ▰▰▰▱▱ 70        ▰▰▱▱▱ 50        ▰▱▱▱▱ 10
```

- Five slots, `▰` filled in the evidence-class colour, `▱` empty in Faint.
- The number follows, because the README documents confidences numerically and
  the output should be greppable against it.
- Always at least one filled slot: a claim that exists is never drawn as zero.

### Coverage Meter

Twelve slots, same glyphs, Foreground rather than an evidence colour, because it
describes the run and not a claim.

### No Findings

```
  no findings                                                     32 files
  ────────────────────────────────────────────────────────────────────────

    notes.md                                        2026-08-24T19:31:08Z
    scratch.bin                                     2026-08-24T19:33:11Z
    ... and 7 more (--limit 0 for all, --json for each)
```

Faint throughout, name left, timestamp right, the name wrapping onto a second
line rather than being cut. It is a list of open questions, not a list of
failures, and it is styled to sit quietly at the end.

Headed `no findings`, not `no recorded origin`. The list holds every file with no
acquisition record, no metadata and nothing that touched it — a wider case than
the old heading named.

**Every one of them is listed by default.** Nobody should have to run the tool a
second time to see a list it already had, which is the same objection that puts
every decoded field on screen without asking. `--brief` caps it at 25 and says
how many are left; an explicit `--limit N` is obeyed as given.

### Metadata Sources

```
  metadata sources                                              12 sources
  ────────────────────────────────────────────────────────────────────────

    OOXML properties     ▰▰▱▱▱   19
    device metadata      ▰▰▰▱▱   18
    XMP                  ▰▰▰▱▱   15
    PDF Info             ▰▰▱▱▱    6
    content credentials  ▰▰▰▱▱    1

  ────────────────────────────────────────────────────────────────────────
    105 files analyzed · 73 with findings · 32 with no findings
```

Aligned columns, ordered by count. The meter repeats each class's confidence so
the table teaches the colour code rather than assuming it.

It answers *which readers produced results*, which is a technical question, so it
sits at the end — after the evidence it describes. It is **not** the findings
section and must not stand in for it: a reader working down a list of parser
names still has to work out what any of it meant.

The closing line counts files. It used to read `70 of 105 files have a recorded
origin`, over the same number the masthead miscounted, and the same objection
applies: most of those files had metadata, not an origin.

The rows are named the way the entries above them are, which for most sources is
the source itself. `document-metadata` is the exception: nine readers answer to
it, so a row saying `document metadata 39` names a category rather than a thing.
Those rows are named by the block instead - `PDF Info`, `OOXML properties`,
`PNG text` - while keeping the colour and the meter of the source behind them,
because what is being reported is still one class of evidence. `device metadata`
keeps its own name: it says the block held a make and a model, which is more
than `EXIF` says.

### Timeline

```
  2026-08-24 19:02:11  invoice-scan.pdf
                     │ https://portal.example.org/billing/2026/invoice-scan.pdf
```

One event per pair of lines, sorted. The rail continues under the timestamp
column so the claim stays tied to its moment.

## 6. Layout & Spacing

- **Min terminal width**: `48` (degrades, stays correct)
- **Design width**: `80`
- **Max width**: `110` — long lines stop being scannable, so the report refuses
  to grow past this even on a wide terminal
- **Gutter**: 2 spaces, then 1 glyph, then 1 space. Content starts at column 4.
- **Label column**: 10 characters, left-aligned, so values line up across labels
- **Field name column**: sized to the names present, to a maximum of 24; a longer
  name takes a line of its own rather than an ellipsis
- **Grid columns**: as many equal-width cells as fit, with a 4-space gap, giving
  way one column at a time down to one. The cells never shrink
- **Gap between entries**: 1 empty line
- **Gap between sections**: 1 empty line above the header, 1 below its rule

### Alignment Principles

- Left-align every name, path, URL and claim
- Right-align every size, count, timestamp and meter
- Never centre anything
- One right-aligned column per line, never two

## 7. Icons & Indicators

| Purpose | Icon | Fallback | Notes |
|---------|------|----------|-------|
| File | `●` | `*` | Evidence-class colour |
| Origin | `←` | `<-` | Evidence-class colour |
| Continuation | `│` | `\|` | Always faint |
| Meter full | `▰` | `#` | Evidence-class colour |
| Meter empty | `▱` | `.` | Faint |
| Rule | `─` | `-` | Faint |
| Separator | `·` | `\|` | Between facts on the source line |
| Contested | `!` | `!` | Notable findings, and a verdict that disagrees with itself |
| Ellipsis | `…` | `...` | Available, and used nowhere in a report |

No emoji, ever: widths are inconsistent and this output gets pasted into
fixed-width documents where a two-column glyph destroys the alignment.

Every glyph has an ASCII fallback, selected when the stream encoding is not
UTF-8. The fallback changes the characters, never the layout.

## 8. Animation & Motion

**None.** The tool prints a report and exits. There is no spinner, no progress
bar, no redraw, and no cursor movement.

This is a design decision, not a gap. The output is routinely redirected to a
file or piped onward, and anything that animates leaves debris when it is. A
scan of a large folder is silent until it is complete.

## 9. Agent Prompt Guide

### Quick Reference

```
Foreground: #d0d0d0  (256: 252)
Muted:      #8a8a8a  (256: 245)
Faint:      #585858  (256: 240)
Recorded:   #5faf87  (256:  71)  green   — another system recorded it
Inherited:  #5fafaf  (256:  73)  cyan    — came out of an archive
Credential: #af87af  (256: 139)  magenta — C2PA, signature unverified
Self:       #5f87af  (256:  68)  blue    — the file's own metadata
Circumst.:  #d7af5f  (256: 179)  yellow  — shell history only
Gutter:     ● ← │    (no boxes, no frames)
Meter:      ▰▱ five slots + number
Style:      forensic, no chrome, colour only ever encodes evidence class
```

### Example Prompts

- "Build a provenance report CLI in the Evidence style: two-space gutter with
  `●` for files, `←` for origins, `│` for continuations, no boxes, colour only
  to encode which class of source made the claim"
- "Render a scan summary: right-align sizes on the name line and a five-slot
  `▰▱` confidence meter on the source line, never both on one line"
- "Group entries by evidence class with lowercase section headers and a faint
  full-width rule, but only when more than one class is present"

## Do's and Don'ts

### Do

- Reserve colour for evidence class. If a thing is not a claim, it is not coloured.
- Keep the gutter to one glyph. It is the whole grouping system.
- Right-align one column per line, never two.
- Give every glyph an ASCII fallback and keep the layout identical under it.
- Print the confidence number next to the meter — the report is evidence and
  should be greppable.
- Say why a result is empty. A pruned browser history is missing evidence, not
  a malfunction, and the report has room to say so.
- Answer the directory before answering the file. Overview, inventory, findings,
  attention, and only then one entry at a time.
- Name a section for what is in it. `file metadata` over `claimed by the file
  itself`; `no findings` over `no recorded origin`.
- Say when a list has been capped, and how to lift the cap.

### Don't

- Don't draw boxes. Nothing here needs a frame, and frames cost width.
- Don't colour a file name, a size or a timestamp. They are facts, not claims.
- Don't animate. The output is piped more often than it is watched.
- Don't print section headers when there is only one section.
- Don't use emoji or any glyph wider than one column.
- Don't let the report exceed 110 columns even when the terminal allows it.
- Don't truncate a name to keep a column. Wrap it, or give the column up.
- Don't call a metadata block a trace. Nothing outside the acquisition sections
  has been traced anywhere.
- Don't let the reader table stand in for the findings. Which parsers returned
  results is not what was found.
- Don't spend `●` on anything that is not a file. It is the gutter's word for
  one, and there is no second one.
- Don't print a namespace URI where a prefix exists. `xmpMM:History/rdf:Seq` is
  a name; the URI spelled out four times is a wall.
- Don't hide part of a list the report already has. Bound it only where a bound
  is stated and countable, and say what it dropped.
