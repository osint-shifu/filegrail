"""The investigation report as one self-contained HTML page.

The same `analysis.Case` the terminal report lays out, with the same sections,
numbers and findings, for a reader who wants to click from a file to its
conflict and back, search a large case, or print it. Dark by default; the print
stylesheet is light.

The page is built to be opened on the machine that holds the case and forwarded
from there, so it can say nothing to anybody else by being opened:

- a Content-Security-Policy that allows no network request of any kind, so even
  a value that slipped past escaping could not fetch anything;
- no external stylesheet, script, font or image, and no `url()` anywhere;
- the only links are to anchors in the page itself - a URL found in a file is
  printed as text, never as something to follow;
- no data embedded in a script: what the page holds is what it shows, so a
  redacted scan cannot leave the value it redacted behind in hidden JSON.

Every value that came out of a file - a name, a path, a field, a URL - is
escaped before it is written.
"""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from . import __version__
from .analysis import NOTHING, REVIEW, Case, CaseFile, Conflict, Finding, named
from .casereport import _ABSENT, _LISTED, MATCHES, _capital, _facts, _folder, _type_name
from .identify import PLACE, Identifier
from .models import ACTIVITY, CATEGORIES, METADATA, ORIGIN, category
from .overview import inventory
from .report import _format, _relative, _size
from .scan import Unsearched

#: Nothing leaves the page: no fetch, no image, no font, no frame, no form.
POLICY = (
    "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
    "img-src data:; base-uri 'none'; form-action 'none'"
)

_STYLE = """
:root{color-scheme:dark;--bg:#0f1216;--panel:#161a20;--panel2:#1d222a;--line:#2a313b;
--text:#d8dce2;--muted:#8e96a1;--faint:#626a75;--origin:#5faf87;--metadata:#6f97c0;
--activity:#d7af5f;--review:#e0895f;--link:#9cc3e6;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
font:14px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--link);text-decoration:none}a:hover{text-decoration:underline}
.mono,dd,td.value,.ref{font-family:var(--mono)}
header.masthead{padding:28px 32px 18px;border-bottom:1px solid var(--line)}
.brand{font:600 12px/1 var(--mono);letter-spacing:.14em;color:var(--muted)}
h1{margin:8px 0 14px;font-size:22px;font-weight:600;letter-spacing:.01em}
dl{margin:0}
.meta,.props{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:3px 18px}
.meta dt,.props dt{color:var(--muted)}
.meta dd,.props dd{margin:0;overflow-wrap:anywhere}
nav{position:sticky;top:0;z-index:5;display:flex;flex-wrap:wrap;gap:6px 16px;
align-items:center;padding:10px 32px;background:rgba(15,18,22,.96);
border-bottom:1px solid var(--line)}
nav a{color:var(--muted);font-size:13px}nav a:hover{color:var(--text)}
.tools{margin-left:auto;display:flex;flex-wrap:wrap;gap:10px;align-items:center;
color:var(--muted);font-size:13px}
.tools input[type=search]{background:var(--panel);border:1px solid var(--line);
color:var(--text);padding:5px 9px;border-radius:4px;min-width:14em;font:inherit}
main{max-width:1180px;margin:0 auto;padding:4px 32px 48px}
section{margin-top:38px}
h2{font-size:13px;letter-spacing:.13em;text-transform:uppercase;color:var(--muted);
font-weight:600;border-bottom:1px solid var(--line);padding-bottom:7px;margin:0 0 16px}
h3{font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);
font-weight:600;margin:24px 0 10px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:6px;
padding:11px 14px}
.card .n{font-size:21px;font-weight:600;font-variant-numeric:tabular-nums}
.card .l{color:var(--muted);font-size:12px}
.card.review{border-color:var(--review)}.card.review .n{color:var(--review)}
.obj{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--faint);
border-radius:6px;padding:12px 16px;margin:10px 0;break-inside:avoid}
.obj.review{border-left-color:var(--review)}
.obj h4{margin:0 0 9px;font-size:15px;font-weight:600;overflow-wrap:anywhere}
.ref{font-size:12px;font-weight:600;color:var(--muted);margin-right:10px}
.obj.review .ref{color:var(--review)}
ul.files{list-style:none;margin:10px 0 0;padding:0}
ul.files li{padding:2px 0;overflow-wrap:anywhere}
.path{color:var(--faint);font-size:12px;overflow-wrap:anywhere}
.note{color:var(--muted);margin:10px 0 0}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:var(--muted);font-weight:500;border-bottom:1px solid var(--line);
padding:6px 8px;white-space:nowrap}
td{border-bottom:1px solid var(--panel2);padding:6px 8px;vertical-align:top;
overflow-wrap:anywhere}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr.review td:first-child{box-shadow:inset 3px 0 var(--review)}
tr.nothing{color:var(--muted)}
.wide{overflow-x:auto}
.origin{color:var(--origin)}.metadata{color:var(--metadata)}.activity{color:var(--activity)}
.state{font:600 11px/1.6 var(--mono);padding:0 6px;border-radius:3px;
border:1px solid var(--line);white-space:nowrap}
.state.found,.state.readable{color:var(--origin);border-color:var(--origin)}
.state.partial{color:var(--activity);border-color:var(--activity)}
.state.missing{color:var(--faint)}
.delta{color:var(--review)}
details{background:var(--panel);border:1px solid var(--line);border-radius:6px;
margin:10px 0;break-inside:avoid}
details.review{border-left:3px solid var(--review)}
summary{cursor:pointer;padding:10px 16px;font-weight:600;overflow-wrap:anywhere}
details>.body{padding:2px 16px 14px}
details.list{background:none;border:0;margin:8px 0 0}
details.list>summary{padding:0;font-weight:400;color:var(--muted)}
h5{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);
margin:16px 0 6px;font-weight:600}
.record{margin:6px 0 10px;padding-left:12px;border-left:1px solid var(--line)}
.record .name{font-weight:600;margin-bottom:3px}
footer{margin-top:52px;border-top:1px solid var(--line);padding-top:12px;
color:var(--faint);font-size:12px}
.hidden{display:none!important}
@media (max-width:720px){header.masthead,nav,main{padding-left:16px;padding-right:16px}
.tools{margin-left:0}}
@media print{:root{color-scheme:light;--bg:#fff;--panel:#fff;--panel2:#e6e6e6;--line:#bdbdbd;
--text:#111;--muted:#4d4d4d;--faint:#6b6b6b;--link:#111;--review:#9c3d14;--origin:#2c6b4b;
--metadata:#2c5a88;--activity:#7d5f18}
body{font-size:10.5px}nav,.tools{display:none}a{color:inherit}
.obj,details,tr,.card{break-inside:avoid}thead{display:table-header-group}
h2{break-after:avoid}}
"""

_SCRIPT = """
(function () {
  var tools = document.getElementById('tools');
  var box = document.getElementById('search');
  var review = document.getElementById('only-review');
  if (!tools || !box) { return; }
  tools.classList.remove('hidden');
  var items = Array.prototype.slice.call(document.querySelectorAll('[data-search]'));
  function apply() {
    var wanted = box.value.trim().toLowerCase();
    var only = review && review.checked;
    items.forEach(function (item) {
      var shown = !wanted || item.textContent.toLowerCase().indexOf(wanted) !== -1;
      if (only && item.dataset.state && item.dataset.state !== 'review') { shown = false; }
      item.classList.toggle('hidden', !shown);
      if (shown && wanted && item.tagName === 'DETAILS') { item.open = true; }
    });
  }
  box.addEventListener('input', apply);
  if (review) { review.addEventListener('change', apply); }
})();
"""

_SECTIONS = (
    ("summary", "Case summary"),
    ("findings", "Key findings"),
    ("coverage", "Evidence coverage"),
    ("conflicts", "Conflicts"),
    ("files", "Files"),
    ("relationships", "Relationships"),
    ("pivots", "Investigative pivots"),
    ("detail", "File detail"),
    ("notes", "Report notes"),
)


def render_html(
    case: Case,
    *,
    verbose: bool = False,
    identifiers: list[Identifier] | None = None,
    content: bool = False,
    home: Path | None = None,
    unsearched: Unsearched | None = None,
    filtered: str = "",
    redacted: bool = False,
    now: datetime | None = None,
) -> str:
    """The whole page. A section with nothing in it is not written."""
    files = {entry.record.path: entry for entry in case.files}
    moment = (now or datetime.now().astimezone()).strftime("%Y-%m-%d %H:%M %Z").strip()
    sections = {
        "summary": _summary(case),
        "findings": _findings(case, files),
        "coverage": _coverage(case, unsearched),
        "conflicts": _conflicts(case, files),
        "files": _files(case),
        "relationships": _relationships(case, files),
        "pivots": _pivots(case, files, verbose=verbose, identifiers=identifiers, content=content),
        "detail": _details(case, files, verbose=verbose),
        "notes": _notes(case),
    }
    present = [(key, title) for key, title in _SECTIONS if sections[key]]

    head = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        f'<meta http-equiv="Content-Security-Policy" content="{POLICY}">',
        '<meta name="referrer" content="no-referrer">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>filegrail · {_e(Path(case.root).name or str(case.root))}</title>",
        f"<style>{_STYLE}</style>",
        "</head>",
        "<body>",
    ]
    meta = [("Target", str(case.root))]
    if home:
        meta.append(("Profile", f"{home} · external"))
    meta.append(("Generated", moment))
    masthead = [
        '<header class="masthead">',
        f'<div class="brand">FILEGRAIL {_e(__version__)}</div>',
        "<h1>Investigation report</h1>",
        _props(meta, css="meta"),
        "</header>",
    ]
    links = " ".join(f'<a href="#{key}">{_e(title)}</a>' for key, title in present)
    nav = [
        f"<nav>{links}",
        '<div class="tools hidden" id="tools">',
        '<input type="search" id="search" placeholder="Search the report" aria-label="Search">',
        '<label><input type="checkbox" id="only-review"> only files to review</label>',
        "</div></nav>",
    ]
    body = ["<main>"]
    for key, title in present:
        body.append(f'<section id="{key}"><h2>{_e(title)}</h2>{sections[key]}</section>')
    if filtered:
        said = "No file matched" if not case.files else "Limited to"
        body.append(f'<p class="note">{_e(said)} {_e(filtered)}.</p>')
    options = [
        ("content", content),
        ("pivots", identifiers is not None),
        ("redaction", redacted),
        ("verbose", verbose),
    ]
    enabled = ", ".join(name for name, on in options if on) or "none"
    body.append(
        "<footer>"
        f"filegrail {_e(__version__)} · generated {_e(moment)} · options: {_e(enabled)} · "
        "this page makes no network requests and loads nothing from outside itself"
        "</footer>"
    )
    body.append("</main>")
    tail = [f"<script>{_SCRIPT}</script>", "</body>", "</html>"]
    return "\n".join(head + masthead + nav + body + tail) + "\n"


# --- pieces ----------------------------------------------------------------------


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def _anchor(ref: str) -> str:
    """The id a report number is found under: `#001` is `file-001`."""
    return f"file-{ref[1:]}" if ref.startswith("#") else ref


def _link(ref: str) -> str:
    return f'<a href="#{_anchor(ref)}">{_e(ref)}</a>'


def _props(pairs: list[tuple[str, str]], css: str = "props") -> str:
    rows = "".join(f"<dt>{_e(label)}</dt><dd>{_e(value)}</dd>" for label, value in pairs)
    return f'<dl class="{css}">{rows}</dl>'


def _name(entry: CaseFile) -> str:
    return Path(entry.record.path).name


def _file_item(case: Case, entry: CaseFile) -> str:
    folder = _folder(case, entry.record)
    path = f' <span class="path">{_e(folder)}</span>' if folder else ""
    return f"<li>{_link(entry.ref)} {_e(_name(entry))}{path}</li>"


def _summary(case: Case) -> str:
    records = [entry.record for entry in case.files]
    contents = inventory(records)
    holding = {name: sum(1 for entry in case.files if entry.found[name]) for name in CATEGORIES}
    known = sum(1 for record in records if record.evidence)
    fields = sum(len(conflict.differences) for conflict in case.conflicts)
    cards = [
        ("Files", f"{len(records):,}", ""),
        ("File types", f"{len(contents.types):,}", ""),
        ("Total size", _size(contents.size), ""),
        ("Files with evidence", f"{known:,} / {len(records):,}", ""),
        ("Origin", f"{holding[ORIGIN]:,}", "origin"),
        ("Metadata", f"{holding[METADATA]:,}", "metadata"),
        ("Activity", f"{holding[ACTIVITY]:,}", "activity"),
        (
            "Conflicts",
            f"{len(case.conflicts)} files / {fields} fields" if case.conflicts else "0",
            "review" if case.conflicts else "",
        ),
        ("Relationships", f"{case.relationships:,}", ""),
    ]
    if case.pivots is not None:
        cards += [
            ("Investigative pivots", f"{case.pivots.total:,}", ""),
            ("Shared pivots", f"{case.pivots.across:,}", ""),
            ("Cross-corpus pivots", f"{case.pivots.cross_corpus:,}", ""),
        ]
    stores = [source for source in case.coverage if source.store]
    if stores:
        found = sum(1 for source in stores if source.state == "found")
        cards.append(("Trace stores found", f"{found} / {len(stores)}", ""))
    shown = []
    for label, value, css in cards:
        number = (
            f'<div class="n {css}">{_e(value)}</div>'
            if css in CATEGORIES
            else (f'<div class="n">{_e(value)}</div>')
        )
        shown.append(
            f'<div class="card {"review" if css == "review" else ""}">'
            f'{number}<div class="l">{_e(label)}</div></div>'
        )
    return f'<div class="cards">{"".join(shown)}</div>'


def _findings(case: Case, files: dict[str, CaseFile]) -> str:
    written = []
    for finding in case.findings:
        written.append(_finding(case, finding, files))
    return "".join(written)


def _finding(case: Case, finding: Finding, files: dict[str, CaseFile]) -> str:
    css = "review" if finding.notable else ""
    facts = [(label, value) for label, value in finding.facts]
    if finding.kind == "generated":
        facts = [fact for fact in facts if fact[0] != "files"]
    parts = [
        f'<article class="obj {css}" id="{finding.ref}" data-search>',
        f'<h4><span class="ref">{finding.ref}</span>{_e(finding.title)}</h4>',
        _props([(_capital(label), value) for label, value in facts]),
    ]
    if finding.kind == "generated":
        for item in finding.items:
            entry = files[item.path]
            parts.append(
                f'<dl class="props"><dt>File</dt><dd>{_link(entry.ref)} {_e(_name(entry))}</dd>'
                + "".join(
                    f"<dt>{_e(_capital(label))}</dt><dd>{_e(value)}</dd>"
                    for label, value in item.facts
                )
                + "</dl>"
            )
    elif finding.items:
        listed = "".join(_file_item(case, files[item.path]) for item in finding.items)
        if finding.kind in _LISTED:
            parts.append(f'<ul class="files">{listed}</ul>')
        else:
            count = len(finding.items)
            parts.append(
                f'<details class="list"><summary>{count} files</summary>'
                f'<ul class="files">{listed}</ul></details>'
            )
    if finding.kind == "no-trace":
        said = "This does not mean the files were never downloaded or transferred."
        if case.begins:
            said += f" Available trace history begins on {case.begins}."
        parts.append(f'<p class="note">{_e(said)}</p>')
    if finding.see:
        target = "conflicts" if finding.see == "CONFLICTS" else "coverage"
        parts.append(f'<p class="note">See <a href="#{target}">{_e(finding.see.lower())}</a>.</p>')
    parts.append("</article>")
    return "".join(parts)


def _coverage(case: Case, unsearched: Unsearched | None) -> str:
    missed = [(path, "could not be read") for path in (unsearched.unreadable if unsearched else [])]
    missed += [(path, "skipped by name") for path in (unsearched.by_name if unsearched else [])]
    if not case.coverage and not missed:
        return ""
    rows = []
    for source in case.coverage:
        state = source.state if source.state in ("found", "readable", "partial") else "missing"
        rows.append(
            f'<tr><td><span class="state {state}">{_e(source.state)}</span></td>'
            f"<td>{_e(source.name)}</td><td>{_e(source.detail)}</td>"
            f'<td class="value">{_e(source.since or "")}</td></tr>'
        )
    for path, why in missed:
        rows.append(
            f'<tr><td><span class="state missing">{_e(why)}</span></td>'
            f'<td class="value">{_e(_relative(path, case.root))}</td><td></td><td></td></tr>'
        )
    table = (
        '<div class="wide"><table><thead><tr><th>Status</th><th>Source</th><th>Detail</th>'
        f"<th>Since</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )
    notes = []
    if case.begins:
        notes.append(f"Observable trace history begins on {case.begins}.")
    if case.coverage:
        notes.append(
            "Absence of origin evidence is not proof that a file was never downloaded, "
            "copied or otherwise transferred to this machine."
        )
    return table + "".join(f'<p class="note">{_e(said)}</p>' for said in notes)


def _conflicts(case: Case, files: dict[str, CaseFile]) -> str:
    return "".join(_conflict(conflict, files) for conflict in case.conflicts)


def _conflict(conflict: Conflict, files: dict[str, CaseFile]) -> str:
    entry = files[conflict.path]
    rows = []
    for difference in conflict.differences:
        span = len(difference.values) + (1 if difference.delta else 0)
        for number, (source, value) in enumerate(difference.values):
            field = f'<td rowspan="{span}">{_e(difference.field)}</td>' if number == 0 else ""
            said = _e(source or "value")
            rows.append(f'<tr>{field}<td>{said}</td><td class="value">{_e(value)}</td></tr>')
        if difference.delta:
            rows.append(
                f'<tr><td>Delta</td><td class="value delta">{_e(difference.delta)}</td></tr>'
            )
    return (
        f'<article class="obj review" id="{conflict.ref}" data-search>'
        f'<h4><span class="ref">{conflict.ref}</span>{_link(entry.ref)} {_e(_name(entry))}</h4>'
        + _props(
            [("Sources", " ↔ ".join(conflict.sources)), ("Fields", str(len(conflict.differences)))]
        )
        + '<div class="wide"><table><thead><tr><th>Field</th><th>Source</th><th>Value</th></tr>'
        f"</thead><tbody>{''.join(rows)}</tbody></table></div></article>"
    )


def _references(entry: CaseFile, kinds: dict[str, str]) -> str:
    said = [_link(ref) for ref in entry.findings if kinds[ref] != "no-trace"]
    said += [_link(ref) for ref in entry.conflicts]
    pivots = f' <span class="path">{_e(" · ".join(entry.pivots))}</span>' if entry.pivots else ""
    return " ".join(said) + pivots


def _files(case: Case) -> str:
    if not case.files:
        return ""
    kinds = {finding.ref: finding.kind for finding in case.findings}
    rows = []
    for entry in case.files:
        folder = _folder(case, entry.record)
        path = f'<div class="path">{_e(folder)}</div>' if folder else ""
        mark = "!" if entry.state == REVIEW else "·" if entry.state == NOTHING else ""
        found = "".join(
            f'<td class="{name}">{_e(" · ".join(entry.found[name]) or "—")}</td>'
            for name in CATEGORIES
        )
        rows.append(
            f'<tr id="{_anchor(entry.ref)}" class="{entry.state}" data-search '
            f'data-state="{entry.state}"><td class="value">{_e(mark)} {_e(entry.ref)}</td>'
            f"<td>{_e(_name(entry))}{path}</td><td>{_e(_format(entry.record.path))}</td>"
            f'<td class="num">{_e(_size(entry.record.size))}</td>{found}'
            f"<td>{_references(entry, kinds)}</td></tr>"
        )
    return (
        '<div class="wide"><table><thead><tr><th>#</th><th>File</th><th>Type</th><th>Size</th>'
        "<th>Origin</th><th>Metadata</th><th>Activity</th><th>References</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _relationships(case: Case, files: dict[str, CaseFile]) -> str:
    rows = []
    for entry in case.files:
        for link in entry.record.links:
            others = [files[path] for path in link.others if path in files]
            related = " ".join(f"{_link(other.ref)} {_e(_name(other))}" for other in others)
            rows.append(
                f"<tr><td>{_link(entry.ref)} {_e(_name(entry))}</td><td>{_e(link.kind)}</td>"
                f"<td>{related or _e(f'{link.count} files')}</td></tr>"
            )
    if not rows:
        return ""
    return (
        '<div class="wide"><table><thead><tr><th>File</th><th>Relationship</th><th>Related</th>'
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _pivots(
    case: Case,
    files: dict[str, CaseFile],
    *,
    verbose: bool,
    identifiers: list[Identifier] | None,
    content: bool,
) -> str:
    pivots = case.pivots
    if pivots is None or not pivots.total:
        return ""
    parts = ["<h3>Summary</h3>", '<div class="wide"><table><tbody>']
    parts += [
        f'<tr><td>{_e(_type_name(kind))}</td><td class="num">{count:,}</td></tr>'
        for kind, count in pivots.by_type
    ]
    parts.append("</tbody></table></div>")
    if pivots.shared:
        parts.append("<h3>Cross-file pivots</h3>")
        for ref, entry in pivots.shared:
            sources = dict.fromkeys(
                place.split(PLACE)[1] for place in entry.where if PLACE in place
            )
            parts.append(
                f'<article class="obj" id="{ref}" data-search>'
                f'<h4><span class="ref">{ref}</span>{_e(entry.type.upper())}</h4>'
                + _props(
                    [
                        ("Value", entry.value),
                        ("Files", f"{entry.files:,}"),
                        ("Sources", " · ".join(sources)),
                    ]
                )
                + "</article>"
            )
    if pivots.dense:
        parts.append("<h3>High-density files</h3>")
        rows = []
        for dense in pivots.dense:
            held = files.get(dense.path)
            name = f"{_link(held.ref)} {_e(Path(dense.path).name)}" if held else _e(dense.path)
            kinds = " · ".join(f"{_type_name(kind)} {count:,}" for kind, count in dense.by_type)
            rows.append(
                f'<tr data-search><td>{name}</td><td class="num">{dense.places:,}</td>'
                f"<td>{_e(kinds)}</td></tr>"
            )
        parts.append(
            '<div class="wide"><table><thead><tr><th>File</th><th>Pivot locations</th>'
            f"<th>By type</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        )
    if verbose and identifiers:
        parts.append(_every_pivot(identifiers))
    else:
        parts.append('<p class="note">Full pivot lists: add -v, or use --json.</p>')
    return "".join(parts)


def _every_pivot(identifiers: list[Identifier]) -> str:
    kinds: dict[str, list[Identifier]] = {}
    for entry in identifiers:
        kinds.setdefault(entry.type, []).append(entry)
    parts = ["<h3>Every pivot</h3>"]
    for kind, entries in kinds.items():
        rows = "".join(
            f'<tr data-search><td class="value">{_e(entry.value)}</td>'
            f'<td class="num">{entry.count:,}</td><td class="num">{entry.files:,}</td>'
            f'<td class="path">{_e(" | ".join(entry.where))}</td></tr>'
            for entry in entries
        )
        parts.append(
            f"<details><summary>{_e(_type_name(kind))} · {len(entries):,}</summary>"
            '<div class="body wide"><table><thead><tr><th>Value</th><th>Count</th><th>Files</th>'
            f"<th>Where (sample)</th></tr></thead><tbody>{rows}</tbody></table></div></details>"
        )
    return "".join(parts)


def _details(case: Case, files: dict[str, CaseFile], *, verbose: bool) -> str:
    findings = {finding.ref: finding for finding in case.findings}
    conflicts = {conflict.ref: conflict for conflict in case.conflicts}
    parts = []
    for entry in case.files:
        wanted = entry.state == REVIEW or entry.found[ORIGIN] or entry.found[ACTIVITY]
        if not (wanted or (verbose and entry.state != NOTHING)):
            continue
        record = entry.record
        facts = [("Type", _format(record.path)), ("Size", _size(record.size))]
        if folder := _folder(case, record):
            facts.append(("Path", folder))
        body = [_props(facts)]
        for name in CATEGORIES:
            held = [found for found in record.evidence if category(found) == name]
            body.append(f'<h5 class="{name}">{_e(name)}</h5>')
            if not held:
                body.append(f'<p class="note">{_e(_ABSENT[name])}</p>')
                continue
            for found in held:
                body.append(
                    f'<div class="record"><div class="name">{_e(named(found))}</div>'
                    f"{_props(_facts(found, name, verbose=verbose))}</div>"
                )
        notes = []
        for ref in entry.conflicts:
            conflict = conflicts[ref]
            fields = " · ".join(difference.field for difference in conflict.differences)
            notes.append(
                f"{_e(' and '.join(conflict.sources))} disagree on {_e(fields)} ({_link(ref)})"
            )
        for ref in entry.findings:
            finding = findings[ref]
            if finding.kind in ("conflicts", "no-trace"):
                continue
            others = [files[item.path] for item in finding.items if item.path != record.path]
            said = f"{_e(finding.title)} ({_link(ref)})"
            if others and len(others) <= 6:
                said += ": " + " · ".join(f"{_link(o.ref)} {_e(_name(o))}" for o in others)
            elif others:
                said += f": with {len(others)} other files"
            notes.append(said)
        if notes:
            body.append("<h5>Analytical notes</h5>")
            body.append(
                '<ul class="files">' + "".join(f"<li>{note}</li>" for note in notes) + "</ul>"
            )
        css = "review" if entry.state == REVIEW else ""
        parts.append(
            f'<details class="{css}" id="detail-{entry.ref[1:]}" open data-search '
            f'data-state="{entry.state}"><summary>{_e(entry.ref)} {_e(_name(entry))}</summary>'
            f'<div class="body">{"".join(body)}</div></details>'
        )
    return "".join(parts)


def _notes(case: Case) -> str:
    records = [entry.record for entry in case.files]
    parts = [
        "<h3>Evidence categories</h3>",
        _props(
            [
                ("Origin", "How a file reached the examined environment."),
                ("Metadata", "What the file records about itself."),
                ("Activity", "What happened to the file locally."),
            ]
        ),
    ]
    used = {found.matched_by for record in records for found in record.evidence}
    if used:
        parts.append("<h3>Match basis</h3>")
        parts.append(
            _props([(basis, meaning) for basis, meaning in MATCHES.items() if basis in used])
        )
    parts.append("<h3>Interpretation</h3>")
    parts.append(
        '<ul class="files">'
        "<li>No origin evidence is not proof that a file was never downloaded or transferred.</li>"
        "<li>Recorded authors, organizations, devices and identifiers are values the files carry, "
        "not verified identity.</li></ul>"
    )
    return "".join(parts)
