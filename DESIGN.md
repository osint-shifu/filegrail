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

### Masthead

```
  filetrail  ~/Downloads                    ▰▰▰▰▰▰▰▱▱▱▱▱  70 of 105 traced
  ────────────────────────────────────────────────────────────────────────
```

Name bold, path faint, coverage meter and count right-aligned. Twelve slots, so
it never reads as one of the five-slot confidence meters.

### Section Header

```
  recorded by another system                                     2 files
  ────────────────────────────────────────────────────────────────────────
```

Printed **only when more than one class is present**. A folder whose files all
resolve the same way gets no headers at all — the grouping would be noise.

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

### Unknown List

```
  no recorded origin (38)
  ────────────────────────────────────────────────────────────────────────

    notes.md                                        2026-08-24T19:31:08Z
    scratch.bin                                     2026-08-24T19:33:11Z
    ... and 33 more (--limit 0 for all, --json for each)
```

Faint throughout, name left, timestamp right. It is a list of open questions,
not a list of failures, and it is styled to sit quietly at the end.

### Summary Table

```
  ────────────────────────────────────────────────────────────────────────
    document metadata    ▰▰▱▱▱   51
    device metadata      ▰▰▰▱▱   18
    content credentials  ▰▰▰▱▱    1

    70 of 105 files have a recorded origin.
```

Aligned columns, ordered by count. The meter repeats each class's confidence so
the summary teaches the colour code rather than assuming it.

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
| Ellipsis | `…` | `...` | Truncation |

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

### Don't

- Don't draw boxes. Nothing here needs a frame, and frames cost width.
- Don't colour a file name, a size or a timestamp. They are facts, not claims.
- Don't animate. The output is piped more often than it is watched.
- Don't print section headers when there is only one section.
- Don't use emoji or any glyph wider than one column.
- Don't let the report exceed 110 columns even when the terminal allows it.
