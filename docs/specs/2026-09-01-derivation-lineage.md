# Derivation lineage

*2026-09-01. Written before any of it was built, and revised only where the
corpus said something the specification did not.*

## The question

A picture arrives in a case directory. It has no download record, no zone
identifier, no shell history — it was copied off a drive. What it does have is
an XMP packet, and inside it four identifiers that Adobe added for exactly this
purpose: `xmpMM:DocumentID`, `xmpMM:InstanceID`, `xmpMM:OriginalDocumentID` and
`xmpMM:DerivedFrom`.

Those identifiers make a file say two things it cannot otherwise say:

- **which document it is a rendition of**, so a web-sized JPEG and the master it
  came from can be recognised as one work rather than two files;
- **what it was made from**, by name, so a chain of edits can be reconstructed
  even when the intermediate files are gone.

`filegrail` already decodes all four and prints them. It does nothing with them.

## What the identifiers mean

From the XMP specification, part 2:

| Property | Identifies | Survives |
|:---|:---|:---|
| `xmpMM:InstanceID` | this exact byte sequence | nothing — it changes on every save |
| `xmpMM:DocumentID` | the document | saves; not a "Save As" into a new document |
| `xmpMM:OriginalDocumentID` | the first document in the chain | the whole lineage |
| `xmpMM:DerivedFrom` | the resource this one was made from | it *is* the edge |

`xmpMM:DerivedFrom` is a `stRef:ResourceRef` structure, so it arrives from the
reader under compound names — `xmpMM:DerivedFrom/stRef:documentID` and
`xmpMM:DerivedFrom/stRef:instanceID`. Both halves matter: the instance names the
bytes, the document names the work.

## What the corpus says

The developer's corpus holds 105 files. Of those:

- 12 carry `xmpMM:InstanceID`, 11 carry `xmpMM:DocumentID`, 2 carry
  `xmpMM:OriginalDocumentID`, and exactly 1 carries a complete `DerivedFrom`
  structure;
- **no identifier is shared by two files.** Across 20 distinct identifiers, the
  graph over this corpus has zero edges.

That last number is the most important thing in this document, and it shapes
everything below. A collection of unrelated files assembled from the internet is
precisely the case where the graph is empty. The graph earns its keep in the
case it was designed for — one photographer's exports, one designer's chain of
saves, one document's renditions — and a design that only looks good on the
happy path would ship as a feature that prints nothing.

Two things the corpus does show:

- `Investigative_Case_File_Review_Final.pdf` carries a complete lineage
  *within itself*: it is a `proof:pdf` rendition of `xmp.did:cd5b91e1…`, derived
  from `xmp.did:dac92226…`, and it and its parent both descend from
  `uuid:5D20892493BFDB11914A8590D31508C8`. Nothing outside the file is needed to
  read that, and it is real evidence about how the PDF was made.
- `MaterialTypeDecisionTreev2.pdf` and its siblings write `DocumentID` and
  `InstanceID` as the *same* uuid. Any matching rule has to compare like with
  like, or PowerPoint exports will appear to be instances of each other.

## Two features, not one

### A. The lineage a file states about itself

Needs no other file. Reads the four identifiers plus `xmpMM:RenditionClass` and
`xmpMM:VersionID` from one XMP packet and states them as a sentence in
`filegrail explain`.

Verifiable against the corpus today, on the one file that carries a full chain.

### B. The links between files in one scan

Indexes every scanned file by its identifiers and reports, per file, which other
files in the same scan it is related to and how.

Not verifiable against this corpus at all — there are no edges in it. It is
verifiable against files built with `exiftool`, which writes the identifiers the
way Adobe's tools do; a three-file chain built that way is decoded correctly by
the existing reader with no changes.

## The relations, and how much each is worth

Ordered by how much a link tells you, strongest first.

| Relation | Reading | Direction |
|:---|:---|:---|
| A's `DerivedFrom/instanceID` = B's `InstanceID` | A was made from exactly these bytes of B | A ← B |
| A's `DerivedFrom/documentID` = B's `DocumentID` | A was made from B's document | A ← B |
| A's `DocumentID` = B's `DocumentID` | two renditions of one document | undirected |
| A's `OriginalDocumentID` = B's `OriginalDocumentID` | a common ancestor, distance unknown | undirected |

The last row is the dangerous one. `osint360-klienci-zastosowania.pdf` in the
corpus carries an `xmp:CreateDate` of 2013 inside a document made in 2026: a
LibreOffice template dragged its whole XMP block along. Everything ever made
from that template shares an `OriginalDocumentID` and shares nothing else.

So a shared `OriginalDocumentID` must never be worded as "derived from". It is
worded as a common ancestor and reported apart from the directed edges.

## Where this can lie

- **An identifier is copied, not earned.** `cp a.jpg b.jpg` produces two files
  with the same `DocumentID` *and* the same `InstanceID`, and no editing
  happened at all. Two files sharing an `InstanceID` are the same bytes or a
  tool that failed to update it; `filegrail` already hashes on request, and the
  report should say which of the two it is when it knows.
- **Templates**, as above.
- **Forgery.** Every one of these values is plain text in a packet nobody signs.
  A link is what the file says, not what happened, and the report must not
  promote it beyond that. This is the same footing as every other metadata
  claim in the tool, and it is already how they are labelled.
- **Collision.** `MaterialTypeDecisionTreev2.pdf` writes one uuid as both its
  document and its instance. Matching must compare `DocumentID` against
  `DocumentID` and `InstanceID` against `InstanceID`, never across.

## Design

### Reading

Nothing new. `read_xmp` already returns all six properties; the lookup is
case-insensitive because writers disagree about `stRef:documentID` versus
`stRef:DocumentID`.

### Structure

A `Lineage` value per file — the identifiers it states — and a `link` between
two files, carrying which relation joined them. Both belong in a new module
rather than in `models.py`: a link is not a claim about where a file came from,
it is a relation between two records, and the three-kind evidence model has no
room for a fourth thing that is not a kind.

### Where it runs

`scan()` already makes one cross-file pass after the per-file loop —
`_attach_archive_origins`, which gives an extracted file the origin of the
archive it came out of. The lineage pass is the same shape and runs beside it.

### What it does *not* do in this version

An ancestor's origin record is **not** inherited down a derivation edge.
The archive case inherits because the bytes were literally inside the archive.
A derived export is a different file, and "the picture this was made from was
downloaded from X" is a sentence a reader should compose, not one the tool
should assert on their behalf. Whether to do it anyway is a decision for the
person who owns the tool, and it is left out until they make it.

### Report surface

The per-file entry gains one line when a link resolves inside the scan, in the
same place the archive inheritance already writes one. A whole-graph view is a
larger question — it is a second axis on a report that currently prints one file
per entry — and it is left for its own design.

## Order of work

1. **A**, the self-stated lineage, because it is small, it is verifiable against
   a real file today, and it makes the identifiers legible before anything tries
   to match them.
2. **B**, the links within a scan, built against `exiftool`-written chains.
3. The whole-graph view and origin inheritance: both need a decision from
   the tool's owner first, and neither is blocked by 1 or 2.
