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
the edge retains the full count.

Every relationship `filegrail` finds between files, identifiers and devices records its kind, its direction and its evidence: source, category, match basis, place, count and, where the evidence has one, time.

For every file, the places where an identifier was found are kept, not only a sample for the whole scan. Where a limit shortens a list, the relationship still states how many there were.

Planned relationships:

- file to identifier, with the source and place, such as `page 3` or `XMP · dc:creator`;
- file to the URL it was downloaded from and to its referrer, from origin records;
- file to file with identical content (SHA-256, with `--hash`);
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

Scan JSON records the options the scan was run with, such as `--pivots`, `--content`, `--home` and filters, and which evidence sources were available. This tells a source with no record of a file apart from a source that could not be searched.

### Graph export as GraphML and CSV

The graph as a file that other tools can import:

- **GraphML**: one file with typed attributes on nodes and relationships, for tools such as Gephi, yEd, Cytoscape, Neo4j (APOC) and NetworkX;
- **CSV edge list**: one relationship per row, with both nodes, their types and the evidence, for table imports such as Maltego, Neo4j `LOAD CSV`, Cytoscape and spreadsheets.

The export includes the scan options and evidence coverage. `--redact` applies to it, and secrets and US Social Security numbers remain fingerprints.

### Relationship explorer in the HTML report

The HTML report gets a view centered on one file or identifier. It shows the neighbors grouped by relationship kind, each with its evidence. Selecting a neighbor moves the view to it.

### Graph export as CASE JSON-LD

The same graph expressed in the CASE/UCO ontology used to exchange digital forensic results. `filegrail` keeps zero runtime dependencies.

## Later

### Comparing two scans

Two saved scans compared by their nodes and relationships: what appeared and what disappeared, for example after a new batch of material arrives.

## Not planned

- Relationships inferred only because two values appear in the same document, such as a name and an email address on one page. Both values are connected to the file, with their places.
- Enrichment, or any other lookup that needs the network.
- A full graph layout in the HTML report.
- A case database and incremental scans.
- Pseudonymized reports and exports.
