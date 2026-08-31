# Changelog

All notable changes to `filetrail` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
the project uses [semantic versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Changed

- Renamed the project to `filetrail`. The previous name was crowded on GitHub,
  including one repository that is the same tool by concept.

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
