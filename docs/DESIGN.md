# Evidence — filegrail TUI Design System

> A forensic report that happens to live in a terminal. Quiet, dense, and
> honest about how much it knows.

Written to the [awesome-tui-design](https://github.com/cola-runner/awesome-tui-design)
`TEMPLATE.md` structure. Every value here is what `src/filegrail/theme.py`
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

A report is read from the directory down to the record, never the other way.
Every view is built from the same five parts in the same order, and a part with
nothing in it is not printed - an empty heading is a promise the scan did not
keep.

| view | sections |
|---|---|
| `filegrail FILE` | `FILE → ORIGIN → METADATA → ACTIVITY → [blocks]` |
| `filegrail DIR` | `SUMMARY → FILES → ORIGIN → METADATA → [ACTIVITY] → [FINDINGS] → [RELATIONSHIPS] → [UNRESOLVED] → [SCAN GAPS]` |
| `--brief` | `SUMMARY → FILES` |
| `explain` | `SUMMARY → ORIGIN → METADATA → [ACTIVITY] → [CORRELATION] → [blocks]` |
| `--timeline` | `TIMELINE` |
| `--content` | `IDENTIFIERS → one section a type → [CROSS-SOURCE MATCHES]` |
| `--cluster` | `CLUSTERS` |
| `compare` | `FILES → METADATA → ORIGIN → CORRELATION → [RELATIONSHIPS]` |
| `doctor` | `SUMMARY → SOURCES → [LIMITATIONS]` |
| `clean --check` | `SUMMARY → RESULTS → [REMAINING METADATA]` |

A single file gets no `SUMMARY` and no `FILES`: there is nothing to summarise
but itself, and a table of one row is ceremony in front of the answer.

**Every count in a heading is of something under it.** `ORIGIN · 2 records · 2
files` means two rows and two distinct files in the table below, and a number
that cannot be checked that way does not go in a heading.

### Two questions, never ranked against each other

Provenance is the whole subject. Under it, an evidence record answers one of
three questions, and the report keeps the three apart:

| | asks | answered by |
|---|---|---|
| **Origin** | how or from where did this reach the environment | browser download history, `Zone.Identifier`, macOS where-from and quarantine, XDG attributes, a fetch command, a `yt-dlp` sidecar, an archive's own origin, a torrent |
| **Metadata** | what does the file record about itself | EXIF, XMP, IPTC, document properties, media tags, mail headers, Content Credentials |
| **Activity** | what happened to it here | Recent Documents, Windows shortcuts, trash records, non-fetch shell history, sync folders, filesystem times |

All three are printed, origin first. Ranking them against each other looks
reasonable and is wrong: a download record used to outrank a camera's EXIF, so a
geotagged photograph that had been downloaded reported its URL and no GPS at
all. The louder record was deleting the more valuable one.

Deliberately not `acquisition`: in digital forensics that word means the
examiner taking custody of material — disk imaging, memory capture, a forensic
copy — and using it for "a browser downloaded this" collides with the one
meaning every examiner already has for it.

### The one idea

**Colour encodes which question a record answers, never how much it is worth.**
Green arrived from somewhere. Blue is the file talking about itself. Amber is
something that happened to it here. Three colours, learned once, and a folder
can be triaged without reading a word. Nothing else in the interface is allowed
to use colour.

## 2. Color Palette

### Semantic Roles

| Role | Hex | ANSI 256 | ANSI 16 | Usage |
|------|-----|----------|---------|-------|
| Background | terminal default | — | — | Never painted; the user's choice wins |
| Foreground | `#d0d0d0` | `252` | `white` | File names, body text |
| Muted | `#8a8a8a` | `245` | `bright black` | Labels, source names, counts |
| Faint | `#585858` | `240` | `bright black` | Rules, rails, timestamps, match basis |
| Warning | `#d7875f` | `173` | `yellow` | Interrupted downloads, contested claims |

### Evidence Categories

The load-bearing part of the palette. Each colour answers "which question does
this record speak to", and it is used for the entry bullet and the record's own
line. One table decides the category and the palette follows it, so a source
cannot be coloured as one thing and reported as another.

| Category | Sources | Hex | 256 | 16 | Reads as |
|-------|---------|-----|-----|----|----------|
| Origin | `browser-download`, `windows-zone-identifier`, `macos-wherefroms`, `macos-quarantine`, `xdg-xattr`, `ytdlp-sidecar`, `email-delivery`, `archive-member`, `torrent`, `messenger-name`, a fetching `shell-history` | `#5faf87` | `71` | `green` | How or from where it reached here |
| Metadata | `device-metadata`, `document-metadata`, `xmp`, `xmp-history`, `iptc`, `c2pa`, `email-header`, `email-relay`, `archive-content` | `#5f87af` | `68` | `blue` | The file's own account of itself |
| Activity | `recent-documents`, `windows-recent`, `freedesktop-trash`, `sync-folder`, `filesystem`, a non-fetching `shell-history` | `#d7af5f` | `179` | `yellow` | Something here handled it |
| None | no evidence found | `#585858` | `240` | `bright black` | Nothing accounts for it |

The order is the order the report prints in, and nothing more. It is not a
ranking: the three answer different questions, so there is no scale they all sit
on.

### Neutral Scale

| Step | Hex | 256 | Usage |
|------|-----|-----|-------|
| 100 | `#3a3a3a` | `237` | Rails between an entry's lines |
| 200 | `#585858` | `240` | Rules, timestamps, the match basis |
| 400 | `#8a8a8a` | `245` | Labels, secondary text |
| 500 | `#d0d0d0` | `252` | Body text, file names |

### Depth Fallback

Resolved once, at startup, from `COLORTERM` and `TERM`:

`truecolor` → `256` → `16` → none. A terminal that cannot colour gets the same
layout in plain text, never a different one.

## 2b. The mark

The logo is not decoration bolted on afterwards; it is this palette, drawn.

Five bars laid on their side so their left ends form the `←` the report uses to
mean *came from*. The palette it was drawn from is this one; the bars are a
mark rather than a legend, and no report reads them as a scale.

**Do not recolour or reorder the bars.** The mark is a signature, and a reader
who has learned the colours in the report should not meet them saying something
else here.

| File | Use |
| --- | --- |
| `assets/filegrail-banner.svg` | 1280×360 README header |
| `assets/filegrail-logo-dark.svg` | horizontal lockup, dark backgrounds |
| `assets/filegrail-logo-light.svg` | horizontal lockup, light backgrounds |
| `assets/filegrail-mark.svg` | square mark, dark backgrounds and favicon |
| `assets/filegrail-mark-light.svg` | square mark, light backgrounds |
| `assets/filegrail-mark-mono.svg` | single colour, for one-colour contexts |

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

Two columns wide: one mark and one space. Every line of every table starts
there, so a marked row and an unmarked row sit in the same column and the eye
never has to shift down a table.

| Glyph | ASCII | Meaning |
|-------|-------|---------|
| `›` | `>` | This row owns the lines under it. Painted in its category. |
| `!` | `!` | This wants a second look. |
| `·` | `.` | No evidence was found here. |
| `│` | `\|` | A field of the record above. Always faint. |
| `└` | `\\` | Its last field. Always faint. |
| *(space)* | | The ordinary case, which needs no announcing. |

Every glyph is one column wide, which is what makes the gutter a gutter.

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

Every field a reader decoded is printed **by default**: the record's own fields
under it, and every metadata block as a table of its own. `--brief` collapses
the lot. A reader who has to run the command a second time to see what the tool
already knew has been told less than it knew.

```
› Chromium download history  recorded-path  2026-08-31 10:49:33
  │ url       https://portal.example.org/press/2026/holiday-master.jpg
  └ referrer  https://portal.example.org/press/
```

Three glyphs, one meaning each, one column.

### Dividers

- Section rule: `─` to the full width, in Faint. Used under the masthead and
  under each section header. Nowhere else.
- No vertical dividers. No section-break ornaments.

## 5. Components

Five parts build every view. Learning them once is learning the whole report.

### Chrome

```
filegrail 0.7.0 · scan
────────────────────────────────────────────────────────────────────────
target    ~/case · profile ~/home · external
```

The name and version, a full-width rule, and the facts about *this run*: what
was looked at, and whose traces were read where they were not this machine's.
One line, wrapped rather than clipped. No profile row on a scan of this machine
- a row saying the profile is the usual one is a row that says nothing.

The mode follows the name where there is one: `· brief`, `· explain`,
`· timeline`, `· doctor`, `· clean --check`.

### Section

```
ORIGIN  ·  2 records · 2 files
────────────────────────────────────────────────────────────────────────
```

A name in capitals, a wide middot, then the counts of what is underneath it
separated by narrow middots. The rule is full width and closes the heading, not
the section - what ends a section is the next heading.

Counts give way from the right when the window cannot hold them. The name never
does.

### Table

```
  file               type  size    origin             metadata
  ─────────────────  ────  ──────  ─────────────────  ────────────────
  press/holiday.jpg  JPEG  3.4 MB  Chromium download  EXIF
· notes.md           MD    64 B    —                  —
```

Headers in lower case; a rule the width of **the column**, not of its name,
because the rule is what says how far the column reaches. Two spaces between
columns. A dash for an empty cell - a blank reads as a value somebody forgot to
print.

Columns give way when the window is too narrow, in an order the table chooses:
on a timeline the category goes first, because colour already carries it and
the verb does not. What is left goes to one flex column, whose cells wrap under
themselves, aligned to their own column. **Nothing is truncated anywhere.**

### Record

```
› Chromium download history  recorded-path  2026-08-31 10:49:33
  │ url       https://portal.example.org/press/2026/holiday-master.jpg
  └ referrer  https://portal.example.org/press/
```

`›` opens a row that owns the lines under it. It carries no analytic meaning at
all - it is there so a record's own line can be told from its fields at a
glance. The fields hang on `│`, the last on `└`, with a label column of their
own so the values line up.

### Marks

| mark | means | where |
|---|---|---|
| `!` | needs a second look | a file whose records disagree, a finding that is a conflict |
| `·` | no evidence found | a file no supported source said anything about |
| `›` | this row owns the lines below | any record with fields |
| *(blank)* | the ordinary case | everything else |

Two rules. A mark is explained under the table that uses it, and only for the
marks that appear. And a fact is marked **once**: a file flagged in `FILES`
appears again in `ORIGIN` and in `FINDINGS`, where what is listed is a record
rather than a file, and a second `!` beside it there would be the report
raising the same alarm twice.

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
- Right-align every size, count, timestamp and match basis
- Never centre anything
- One right-aligned column per line, never two

## 7. Icons & Indicators

| Purpose | Icon | Fallback | Notes |
|---------|------|----------|-------|
| Record | `›` | `>` | Category colour |
| Needs review | `!` | `!` | Warning colour |
| No evidence | `·` | `.` | Faint |
| Field | `│` | `\|` | Always faint |
| Last field | `└` | `\\` | Always faint |
| Rule | `─` | `-` | Faint |
| Separator | `·` | `\|` | Between facts on one line |
| Not equal | `≠` | `!=` | Between two values that disagree |
| Empty cell | `—` | `-` | Faint |
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
Origin:     #5faf87  (256:  71)  green   — how or from where it reached here
Metadata:   #5f87af  (256:  68)  blue    — what the file says about itself
Activity:   #d7af5f  (256: 179)  yellow  — what handled it here
Gutter:     › ! · │ └   (no boxes, no frames)
Marks:      ! needs review · no evidence found
Style:      forensic, no chrome, colour only ever encodes the category
```

### Example Prompts

- "Build a provenance report CLI in the Evidence style: a two-column gutter
  with `›` opening a record and `│`/`└` for its fields, tables whose rules are
  the width of the column, no boxes, colour only to encode which question a
  record answers"
- "Render a scan summary: right-align sizes on the name line and the match
  basis on the source line, never both on one line"
- "Group entries by evidence category with lowercase section headers and a
  faint full-width rule, but only when more than one category is present"

## Do's and Don'ts

### Do

- Reserve colour for the evidence category. If a thing is not a record, it is not coloured.
- Keep the gutter to one glyph. It is the whole grouping system.
- Right-align one column per line, never two.
- Give every glyph an ASCII fallback and keep the layout identical under it.
- Print how a record was matched to the file. It is the difference between a
  path and a name that happened to be the same, and it is greppable.
- Say why a result is empty. A pruned browser history is missing evidence, not
  a malfunction, and the report has room to say so.
- Answer the directory before answering the record. Summary, files, and only
  then the records grouped by the question each one answers.
- Name a section for what is in it. `file metadata` over `claimed by the file
  itself`; `no evidence found` over `no recorded origin`.
- Say when a list has been capped, and how to lift the cap.

### Don't

- Don't draw boxes. Nothing here needs a frame, and frames cost width.
- Don't colour a file name, a size or a timestamp. They are facts, not claims.
- Don't animate. The output is piped more often than it is watched.
- Don't print section headers when there is only one section.
- Don't use emoji or any glyph wider than one column.
- Don't let the report exceed 110 columns even when the terminal allows it.
- Don't truncate a name to keep a column. Wrap it, or give the column up.
- Don't call a metadata block a trace. Nothing outside the origin sections
  has been traced anywhere.
- Don't put a count in a heading that a reader cannot go and count underneath
  it.
- Don't mark the same fact twice. A file flagged in `FILES` appears again in
  `ORIGIN` and in `FINDINGS`, and a second `!` there is the same alarm raised
  again.
- Don't print a namespace URI where a prefix exists. `xmpMM:History/rdf:Seq` is
  a name; the URI spelled out four times is a wall.
- Don't hide part of a list the report already has. Bound it only where a bound
  is stated and countable, and say what it dropped.
