# Roadmap

Planned work, in the order it will be done. Released changes are listed in [CHANGELOG.md](CHANGELOG.md).

## Investigation graph

`filegrail` will turn a scan into a graph of files, identifiers and the relationships between them. Every relationship carries the evidence it came from. The graph can be exported to graph and link-analysis tools, where the identifiers can be enriched and analyzed further.

`filegrail` stays local and makes no network requests. Enrichment happens in the tool the graph is imported into.

### Relationships backed by evidence

The first relationship is implemented in scan JSON: `--pivots` and `--content`
connect every file to its normalized identifiers. Each edge keeps its source,
exact place, corpus and occurrence count, plus category, match basis and time
where the underlying evidence has them. A long list of places is bounded while
the edge retains the full count. Origin URLs and referrers have specific edges;
derived edges connect an email or URL to its domain and a recognized digest to
the clear email address it identifies. With `--hash`, files with identical
content meet at one shared SHA-256 node instead of producing a quadratic list
of file-to-file edges. The author, camera model and camera body serial already
used by clustering are also nodes, with their metadata block and field on the
edge. Archive and torrent matches record the container path directly and become
membership edges without parsing a prose note. Existing XMP lineage links become
file-to-file edges with the exact matching fields from both files.

Every relationship `filegrail` finds between files, identifiers and devices records its kind, its direction and its evidence: source, category, match basis, place, count and, where the evidence has one, time.

For every file, the places where an identifier was found are kept, not only a sample for the whole scan. Where a limit shortens a list, the relationship still states how many there were.

Planned relationships:

- file to identifier, with the source and place, such as `page 3` or `XMP · dc:creator`;
- file to the URL it was downloaded from and to its referrer, from origin records;
- file to a shared content digest (SHA-256, with `--hash`);
- file to camera, by serial number or model, and file to author;
- digest to the address it is a digest of;
- email address to domain, and URL to host and domain, marked as derived from the value itself rather than from a file.

A value shared by many files is one node connected to each of them, not a connection between every pair of files.

### XMP derivation as relationships

Relationships between files read from XMP document identifiers, such as derived-from and same-document, become relationships of the graph. The `links` field in JSON keeps its current form, and the `filegrail.scan/2` schema stays the same.

### Archive and torrent membership as relationships

A file matched to an archive or a torrent is connected to it, with the match basis, such as name and size.

### Relationships in JSON

Scan JSON gains a section listing nodes and relationships, each relationship with its evidence.

Node identifiers are built from the type and normalized value, such as `email:ann@example.org`, so the same value from two scans becomes one node in the tool that imports them.

The section is an addition, so the schema version does not change.

### Scan options and evidence coverage in JSON

Implemented. Scan JSON records the effective options, profile and filters under
`run`. `coverage` records each evidence source as searched, unavailable,
partial or disabled, with artifact and record counts plus skipped and unreadable
paths. These values are collected during the scan rather than by rereading the
profile afterward.

### Graph export as GraphML and CSV

Implemented as `--graphml` and `--graph-csv`, with `-o` for a destination file:

- **GraphML**: one file with typed attributes on nodes and relationships, for tools such as Gephi, yEd, Cytoscape, Neo4j (APOC) and NetworkX;
- **CSV edge list**: one relationship per row, with both nodes, their types and the evidence, for table imports such as Maltego, Neo4j `LOAD CSV`, Cytoscape and spreadsheets.

`--redact` applies before the graph is built, and secrets and US Social Security
numbers remain fingerprints. Scan options and evidence coverage are stored as
GraphML graph attributes and repeated on each CSV relationship row.

### Relationship explorer in the HTML report

Implemented. The HTML report can focus on any connected file, identifier,
person or device, filter its relationships by kind and inspect the evidence for
every edge. Selecting either endpoint moves the focus to that node. A picture
of the connected part of the graph, laid out at render time without any
library, sits above the explorer; clicking a node focuses it. The picture is
bounded to the nodes that carry the shape of the case, and the table keeps the
rest.

### Graph export as CASE JSON-LD

The same graph expressed in the CASE/UCO ontology used to exchange digital forensic results. `filegrail` keeps zero runtime dependencies.

## Evidence depth

The next round deepens what a scan knows about a file before widening the list of formats. Formats come last, and only the ones that turn up in real material.

### Real files behind every reader

Readers written against a specification alone are checked against files produced by the software the specification describes, and the defects those files reveal are fixed. The corpus test already runs over `test-data/`; what is missing is the files.

### Where a value was found

Every evidence record can say where in the file it was read: the archive member, the embedded object or stream, the metadata namespace and path, the logical place such as a page or a slide, and the byte range where one is reliable. The `place` a person reads stays; the structured location is added beside it, in scan JSON without a schema change.

### Files inside files

Embedded objects are read as children of the file that carries them: an archive member, an OLE object in a document, an attachment in a message, a file embedded in a PDF, each with its own evidence and its own location, connected to its parent as a relationship of the graph. Depth, count, size and total work are bounded by one budget, so a container cannot make a scan run without end.

### Content Credentials in every container that carries them

C2PA manifests are read from TIFF and DNG, WAV and AVI, MP4, MOV, M4A, HEIF and AVIF, and ID3, using the container readers that already exist. Ingredients and actions are read in their current form, and the `c2pa.ai-disclosure` assertion and the IPTC AI fields are reported as declared AI provenance: a declaration, never a verdict about the content. The claim signature stays unverified and the report keeps saying so.

### Deeper Office and PDF evidence

From Office documents: external relationships, attached templates and linked workbooks, the original name and path of embedded objects, and DDE fields, each reported as an observation. From PDF: what each incremental update changed, object by object, so a document edited after signing shows which objects the edit replaced or added.

### What a media file says about how it was made

From MP4, MOV, Matroska and RIFF: the encoder chain, the recording device, timecode, and the language of subtitle and audio tracks. Codec profiles, colour and bit rates are left out; they describe the picture, not where it came from.

### Format identification from the bytes

The signature check grows into format identification: the format and its version from the file's bytes, named by the PRONOM registry and its persistent identifiers, from a versioned snapshot of the registry compiled into the package. The extension stays a claim the bytes confirm or contradict.

### Formats that turn up in real material

Canon CR3 and Fujifilm RAF, TNEF `winmail.dat`, and the member list of 7z and RAR archives without unpacking them. Each is added only once a real file is available to check it against.

## Later

### Comparing two scans

Two saved scans compared by their nodes and relationships: what appeared and what disappeared, for example after a new batch of material arrives.

## Not planned

- Relationships inferred only because two values appear in the same document, such as a name and an email address on one page. Both values are connected to the file, with their places.
- Enrichment, or any other lookup that needs the network.
- A case database and incremental scans.
- Pseudonymized reports and exports.
