"""The investigation report as one self-contained HTML page.

The same `analysis.Case` the terminal report lays out, with the same sections,
numbers and findings, for a reader who wants to click from a file to its
conflict and back, search a large case, or print it. Dark by default, with a
light theme a button away and a light print stylesheet.

The page is built to be opened on the machine that holds the case and forwarded
from there, so it can say nothing to anybody else by being opened:

- a Content-Security-Policy that allows no network request of any kind, so even
  a value that slipped past escaping could not fetch anything;
- no external stylesheet, script, font or image, and no `url()` anywhere; the
  mark in the masthead and the tab icon are inline drawings;
- the only links are to anchors in the page itself - a URL found in a file is
  printed as text, never as something to follow;
- no data embedded in a script: what the page holds is what it shows, so a
  redacted scan cannot leave the value it redacted behind in hidden JSON.

Every value that came out of a file - a name, a path, a field, a URL - is
escaped before it is written.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path

from . import __version__
from .analysis import NOTHING, REVIEW, Case, CaseFile, Conflict, Finding, Pivots, named
from .casereport import _ABSENT, _LISTED, _PER_FILE, _capital, _facts, _type_name
from .graph import Graph, Node, Relationship, build_graph
from .identify import PLACE, Identifier
from .models import (
    ACTIVITY,
    CATEGORIES,
    EMBEDDED,
    FILE_ATTRIBUTE,
    ORIGIN,
    RECORDED_PATH,
    EvidenceRecord,
    category,
)
from .overview import inventory
from .report import _format, _relative, _size, _stamp, shown
from .scan import Unsearched

#: Nothing leaves the page: no fetch, no image, no font, no frame, no form.
POLICY = (
    "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
    "img-src data:; base-uri 'none'; form-action 'none'"
)

#: The mark, drawn in the page in the accent.
_MARK = (
    '<svg class="mark" viewBox="0 0 144 204" aria-hidden="true">'
    '<path fill="var(--accent)" fill-rule="evenodd" d="M24,48 A48,48 0 0 1 72,0 H108 V24 '
    "H72 A24,24 0 0 0 48,48 V72 H144 V96 A60,60 0 0 1 96,154.79 V180 H132 V204 H36 V180 "
    'H72 V154.79 A60,60 0 0 1 24,96 H0 V72 H24 Z M48,96 H120 A36,36 0 0 1 48,96 Z"/></svg>'
)

#: The same mark as the tab icon. A data URI: drawn by the browser, fetched from nowhere.
_FAVICON = (
    '<link rel="icon" href="data:image/svg+xml,'
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 144 204'%3E"
    "%3Cpath fill='%235FA89A' fill-rule='evenodd' d='M24,48 A48,48 0 0 1 72,0 H108 V24 "
    "H72 A24,24 0 0 0 48,48 V72 H144 V96 A60,60 0 0 1 96,154.79 V180 H132 V204 H36 V180 "
    "H72 V154.79 A60,60 0 0 1 24,96 H0 V72 H24 Z M48,96 H120 A36,36 0 0 1 48,96 Z'/%3E"
    '%3C/svg%3E">'
)

#: Files a pivot names before the rest go behind a summary: enough to see the
#: shape of the group, few enough to keep the row a row.
_HOLDERS = 6

#: Places a pivot shows of the twenty it keeps. Grouping them by file and
#: source collapses the repeats, so more of them fit in fewer lines.
_SAMPLE = 8

#: Bases that tie a record to this exact file rather than to a name it shares.
_STRONG = frozenset({EMBEDDED, FILE_ATTRIBUTE, RECORDED_PATH})

_STYLE = """
:root{color-scheme:dark;
--bg:#0F1115;--surface:#151920;--surface-2:#1B2027;--line:#262A31;--line-2:#333944;
--ink:#E6E8EB;--ink-2:#C3C8CE;--muted:#9AA1A9;--faint:#6B727B;
--accent:#5FA89A;--accent-ink:#0F1115;--accent-soft:rgba(95,168,154,.14);
--origin:#5FA89A;--metadata:#7FA3C7;--activity:#C9A66B;--alert:#D08770;
--alert-soft:rgba(208,135,112,.14);
--mono:"IBM Plex Mono","JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
--r:6px;--gutter:clamp(20px,4vw,56px)}
[data-theme=light]{color-scheme:light;
--bg:#F4F5F6;--surface:#FFFFFF;--surface-2:#EEF0F2;--line:#DDE0E4;--line-2:#C9CDD3;
--ink:#0F1115;--ink-2:#2C3138;--muted:#5D646C;--faint:#8A9098;
--accent:#2F8677;--accent-ink:#FFFFFF;--accent-soft:rgba(47,134,119,.12);
--origin:#2F8677;--metadata:#3E6F9E;--activity:#8E6E2E;--alert:#B5563A;
--alert-soft:rgba(181,86,58,.12)}
*{box-sizing:border-box}
html{scroll-padding-top:120px}
body{margin:0;background:var(--bg);color:var(--ink);font:13px/1.55 var(--mono);
font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline;text-underline-offset:3px}
code{font:inherit}
button{font:inherit;color:inherit;background:none;border:0;padding:0;cursor:pointer}
::selection{background:var(--accent);color:var(--accent-ink)}

.mast{padding:40px var(--gutter) 28px;border-bottom:1px solid var(--line);display:grid;
grid-template-columns:auto 1fr auto;gap:28px;align-items:start}
.mast .mark{width:49px;height:69px;flex:none}
.mast .who{align-self:center}
.mast .word{font-size:28px;font-weight:500;letter-spacing:-.5px;line-height:1;margin:2px 0 6px}
.mast .word small{font-size:12px;font-weight:400;letter-spacing:.1em;color:var(--muted);
margin-left:12px;vertical-align:middle}
.mast .tag{font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted)}
.facts{grid-column:1/-1;display:grid;grid-template-columns:auto 1fr;gap:4px 16px;
font-size:12px;margin:24px 0 0;max-width:860px;padding:16px 0 0;
border-top:1px solid var(--line)}
.facts dt{color:var(--muted)}
.facts dd{margin:0;color:var(--ink-2);overflow-wrap:anywhere}
.mast-actions{display:none;gap:8px;align-items:center}
.js .mast-actions{display:flex}
.btn{display:inline-flex;align-items:center;gap:8px;height:30px;padding:0 12px;
border:1px solid var(--line-2);border-radius:var(--r);color:var(--ink-2);font-size:12px;
white-space:nowrap}
.btn:hover{border-color:var(--accent);color:var(--ink)}
.btn.icon{width:30px;padding:0;justify-content:center;font-size:14px}

.nav{position:sticky;top:0;z-index:20;background:var(--bg);border-bottom:1px solid var(--line);
padding:0 var(--gutter);display:flex;align-items:center;gap:6px;height:48px;overflow-x:auto}
.nav a{color:var(--muted);font-size:11px;letter-spacing:.14em;text-transform:uppercase;
padding:0 10px;height:48px;display:inline-flex;align-items:center;gap:8px;
border-bottom:2px solid transparent;white-space:nowrap}
.nav a b{font-weight:400;color:var(--faint)}
.nav a:hover{color:var(--ink);text-decoration:none}
.nav a.on{color:var(--ink);border-bottom-color:var(--accent)}
.nav a.on b{color:var(--accent)}
.nav .sp{flex:1}
.nav .home{display:none;align-items:center;height:48px;padding:0 14px 0 0}
.js .nav.scrolled .home{display:inline-flex}
.nav .home .mark{width:18px;height:25px}
.nav .home:hover{text-decoration:none}
.btn[data-expand]{display:none}
.js .btn[data-expand]{display:inline-flex}
.nav .btn{margin-right:8px}
.h .btn{margin-left:auto}
.search{position:relative;flex:none;display:none}
.js .search{display:block}
.search input{height:30px;width:260px;background:var(--surface);border:1px solid var(--line-2);
border-radius:var(--r);color:var(--ink);padding:0 30px 0 10px;font:inherit;font-size:12px}
.search input:focus{outline:none;border-color:var(--accent)}
.search kbd{position:absolute;right:8px;top:7px;font-size:10px;color:var(--faint);
border:1px solid var(--line-2);border-radius:3px;padding:0 4px;line-height:14px}
.search .hits{position:absolute;right:34px;top:8px;font-size:11px;color:var(--accent)}

main{padding:0 var(--gutter) 80px}
section{padding:44px 0 8px;border-bottom:1px solid var(--line)}
section:last-of-type{border-bottom:0}
.h{display:flex;align-items:baseline;gap:14px;margin:0 0 18px;flex-wrap:wrap}
.h h2{margin:0;font-size:12px;font-weight:500;letter-spacing:.22em;text-transform:uppercase}
.h .n{color:var(--accent);font-size:12px}
.h .n b{font-weight:400;color:var(--muted)}
h3{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);
font-weight:400;margin:22px 0 8px}
p.note{color:var(--muted);font-size:12px;margin:12px 0 0;max-width:92ch}

.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;
background:var(--line);border:1px solid var(--line);border-radius:var(--r);overflow:hidden}
.card{background:var(--surface);padding:16px 18px 14px;display:flex;flex-direction:column;
gap:6px;color:inherit;position:relative}
a.card:hover{background:var(--surface-2);text-decoration:none}
.card .v{font-size:26px;line-height:1;font-weight:500;letter-spacing:-.5px}
.card .v .of{color:var(--faint);font-size:16px}
.card .k{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.card .s{font-size:11px;color:var(--faint);overflow-wrap:anywhere}
.card.alert .v{color:var(--alert)}
.card.accent .v{color:var(--accent)}
.card.origin .v{color:var(--origin)}
.card.metadata .v{color:var(--metadata)}
.card.activity .v{color:var(--activity)}
a.card:after{content:"\\2192";position:absolute;right:14px;top:14px;color:var(--faint);
font-size:12px}
a.card:hover:after{color:var(--accent)}
.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:11px;color:var(--muted);margin:14px 0 0}

.tbl{width:100%;border-collapse:collapse;font-size:12px}
.tbl th{text-align:left;font-weight:400;font-size:10.5px;letter-spacing:.14em;
text-transform:uppercase;color:var(--muted);padding:8px 12px 8px 0;
border-bottom:1px solid var(--line-2);white-space:nowrap;user-select:none}
.tbl th[data-sort]{cursor:pointer}
.tbl th[data-sort]:hover,.tbl th[data-sort]:focus{color:var(--ink);outline:none}
.tbl th .dir{color:var(--accent);margin-left:4px;font-size:10px}
.tbl td{padding:9px 12px 9px 0;border-bottom:1px solid var(--line);vertical-align:top;
color:var(--ink-2)}
.tbl tr:last-child td{border-bottom:0}
.tbl tbody tr:hover td{background:var(--surface)}
.tbl td.num,.tbl th.num{text-align:right;padding-right:12px;white-space:nowrap}
.tbl th.num{letter-spacing:.04em}
.tbl .id{color:var(--muted);white-space:nowrap}
.tbl .path{color:var(--ink);overflow-wrap:anywhere;min-width:18em}
.tbl .val{color:var(--ink);overflow-wrap:anywhere;min-width:16em;max-width:26em}
.tbl .dim{color:var(--faint)}
.tbl .where{color:var(--faint);overflow-wrap:break-word;min-width:26em}
.tbl .found{max-width:22em}
.tbl details{margin-top:4px}
.tbl summary{cursor:pointer;color:var(--accent)}
.tbl tr[hidden]{display:none}
.tbl tr.hit td{background:var(--accent-soft)}
.wrap{overflow-x:auto}
.wrap>table.index,.wrap>table.pivots{min-width:860px}
.wrap>table.relationships{min-width:940px}

.rel-controls{display:flex;align-items:end;gap:14px;flex-wrap:wrap;margin:0 0 12px}
.rel-controls label{display:grid;gap:5px;min-width:min(100%,34em);color:var(--muted);
font-size:10.5px;letter-spacing:.12em;text-transform:uppercase}
.rel-controls select{width:100%;height:34px;padding:0 34px 0 10px;border:1px solid var(--line-2);
border-radius:var(--r);background:var(--surface);color:var(--ink);font:12px/1.4 var(--mono)}
.rel-controls select:hover,.rel-controls select:focus{border-color:var(--accent);outline:none}
.rel-count{color:var(--muted);font-size:12px;padding-bottom:7px}
.rel-kinds{display:none;flex-wrap:wrap;gap:6px;margin:0 0 14px}
.js .rel-kinds{display:flex}
.rel-node{display:flex;align-items:flex-start;gap:8px;min-width:17em}
.rel-node .pill{margin-top:1px}
.rel-node a,.rel-node .v{overflow-wrap:anywhere}
.rel-focus{display:none;align-items:center;justify-content:center;flex:none;width:22px;height:22px;
border:1px solid var(--line-2);border-radius:3px;color:var(--faint);margin-left:auto}
.js .rel-focus{display:inline-flex}
.rel-focus:hover,.rel-focus:focus{color:var(--accent);border-color:var(--accent);outline:none}
.relationship .arrow{color:var(--faint);font-size:16px;text-align:center}
.relationship .kind{color:var(--ink);min-width:13em}
.relationship .kind .dim{display:block;margin-top:2px}
.relationship details{min-width:18em}
.rel-proof{padding:8px 0;border-bottom:1px solid var(--line)}
.rel-proof:last-child{border-bottom:0}
.rel-proof .fields{grid-template-columns:minmax(80px,max-content) 1fr;margin-top:0}

.cat{display:inline-flex;align-items:center;gap:6px;font-size:11px;letter-spacing:.06em;
color:var(--ink-2);white-space:nowrap}
.cat:before{content:"";width:8px;height:8px;border-radius:2px;background:var(--c,var(--faint));
flex:none}
.cat.origin{--c:var(--origin)}
.cat.metadata{--c:var(--metadata)}
.cat.activity{--c:var(--activity)}
.cat.none{--c:transparent;box-shadow:inset 0 0 0 1px var(--line-2);color:var(--faint)}
.cat.none:before{box-shadow:inset 0 0 0 1px var(--line-2)}
.dots{display:inline-flex;gap:4px;vertical-align:middle}
.dots i{width:8px;height:8px;border-radius:2px;background:var(--line-2)}
.dots i.o{background:var(--origin)}
.dots i.m{background:var(--metadata)}
.dots i.a{background:var(--activity)}
.flag{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;
border-radius:3px;background:var(--alert-soft);color:var(--alert);font-weight:500}
.pill{display:inline-block;font-size:10.5px;letter-spacing:.08em;padding:1px 7px;
border-radius:999px;border:1px solid var(--line-2);color:var(--muted);white-space:nowrap}
.pill.match{border-color:transparent;background:var(--surface-2);color:var(--ink-2)}
.pill.strong{border-color:var(--accent);background:none;color:var(--accent)}
.chips{display:none;flex-wrap:wrap;gap:6px;margin:0 0 16px}
.js .chips{display:flex}
.chip{height:26px;padding:0 10px;border:1px solid var(--line-2);border-radius:999px;
font-size:11px;color:var(--muted);display:inline-flex;align-items:center;gap:6px}
.chip b{font-weight:400;color:var(--faint)}
.chip:hover{color:var(--ink);border-color:var(--ink-2)}
.chip.on{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.chip.on b{color:var(--accent-ink);opacity:.7}
.copy{display:none;color:var(--faint);margin-left:6px;vertical-align:middle;opacity:0}
.js .copy{display:inline}
tr:hover .copy,.rec:hover .copy,dd:hover .copy,.pair:hover .copy,.facts dd:hover .copy{opacity:1}
.copy:hover,.copy:focus{color:var(--accent);opacity:1;outline:none}
.copy.ok{color:var(--accent);opacity:1}

.find{display:grid;grid-template-columns:44px 1fr;gap:0 16px;padding:14px 0;
border-bottom:1px solid var(--line)}
.find:last-child{border-bottom:0}
.find .fid{color:var(--accent)}
.find .t{color:var(--ink);overflow-wrap:anywhere}
.find .t.warn:before{content:"!";display:inline-flex;align-items:center;justify-content:center;
width:16px;height:16px;border-radius:3px;background:var(--alert-soft);color:var(--alert);
margin-right:8px;font-size:11px;vertical-align:1px}
.find .files{margin-top:6px;display:flex;flex-wrap:wrap;gap:4px 12px;font-size:12px;
color:var(--muted)}
.find .files a{color:var(--ink-2)}
.find details .files{display:grid;gap:2px;margin-top:8px}
.find .note{color:var(--muted);font-size:12px;margin-top:6px;max-width:92ch}
.find details{margin-top:6px}
.find summary{color:var(--accent);font-size:12px;cursor:pointer}

.tabs{display:none;flex-wrap:wrap;gap:2px 0;border-bottom:1px solid var(--line-2);
margin-bottom:14px}
.js .tabs{display:flex}
.tabs button{padding:8px 12px;font-size:11px;letter-spacing:.1em;text-transform:uppercase;
color:var(--muted);border-bottom:2px solid transparent;margin-bottom:-1px;white-space:nowrap}
.tabs button b{font-weight:400;color:var(--faint);margin-left:6px}
.tabs button.on{color:var(--ink);border-bottom-color:var(--accent)}
.tabs button.on b{color:var(--accent)}
.js .pane{display:none}
.js .pane.on{display:block}
.pane:before{content:attr(data-label);display:none;font-size:10px;letter-spacing:.14em;
text-transform:uppercase;color:var(--muted);margin:14px 0 6px}
.holder{display:block;white-space:nowrap}

.file{border:1px solid var(--line);border-radius:var(--r);margin:0 0 14px;background:var(--surface)}
.file>summary{list-style:none;display:grid;grid-template-columns:44px 1fr auto;gap:16px;
align-items:center;padding:12px 16px;cursor:pointer}
.file>summary::-webkit-details-marker{display:none}
.file>summary .id{color:var(--muted)}
.file>summary .name{color:var(--ink);overflow-wrap:anywhere}
.file>summary .meta{color:var(--faint);font-size:11px;display:flex;gap:14px;align-items:center;
flex-wrap:wrap}
.file>summary .chev{color:var(--faint)}
.file[open]>summary .chev{transform:rotate(90deg)}
.file[open]>summary{border-bottom:1px solid var(--line)}
.file.review{border-left:2px solid var(--alert)}
.rec{display:grid;grid-template-columns:96px 1fr;gap:0 20px;padding:12px 16px;
border-bottom:1px solid var(--line)}
.rec>.fields{grid-column:2}
.rec:last-child{border-bottom:0}
.rec .cat{align-self:start;margin-top:2px}
.rec .src{color:var(--ink);display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.rec .note{color:var(--muted);margin-top:2px}
.rec.silent,.rec.silent .src{color:var(--faint)}
.fields{display:grid;grid-template-columns:minmax(120px,max-content) 1fr;gap:3px 18px;
margin:8px 0 0;font-size:12px}
.fields dt{color:var(--muted);white-space:nowrap}
.fields dd{margin:0;color:var(--ink-2);overflow-wrap:anywhere}
.extra{display:grid;grid-template-columns:96px 1fr;gap:0 20px;padding:12px 16px;
border-top:1px dashed var(--line);font-size:12px}
.extra .k{color:var(--muted);letter-spacing:.14em;text-transform:uppercase;font-size:10.5px;
padding-top:2px}
.extra ul{margin:0;padding:0;list-style:none;display:grid;gap:4px}
.extra li{color:var(--ink-2);overflow-wrap:anywhere}

.conf{display:grid;grid-template-columns:44px 1fr;gap:0 16px;padding:14px 0;
border-bottom:1px solid var(--line)}
.conf:last-child{border-bottom:0}
.conf .cid{color:var(--alert)}
.conf .t{color:var(--ink);overflow-wrap:anywhere}
.conf .field{color:var(--muted);font-size:11px;letter-spacing:.14em;text-transform:uppercase;
margin:12px 0 0}
.conf .pair{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,18em),1fr));
gap:1px;background:var(--line);border:1px solid var(--line);border-radius:var(--r);
overflow:hidden;margin-top:6px;font-size:12px}
.conf .pair>div{background:var(--surface);padding:10px 14px}
.conf .pair .src{color:var(--muted);font-size:11px;letter-spacing:.1em;text-transform:uppercase;
margin-bottom:4px}
.conf .pair .v{color:var(--ink);overflow-wrap:anywhere}
.conf .delta{margin-top:8px;color:var(--alert)}

footer{padding:24px var(--gutter);border-top:1px solid var(--line);display:flex;
justify-content:space-between;flex-wrap:wrap;gap:10px;font-size:11px;letter-spacing:.14em;
text-transform:uppercase;color:var(--faint)}

@media (max-width:820px){
.mast{grid-template-columns:auto 1fr}
.mast-actions{grid-column:1/-1}
.rec{grid-template-columns:1fr}
.rec .cat{margin-bottom:4px}
.rec>.fields{grid-column:1}
.extra{grid-template-columns:1fr}
.search input{width:150px}
.rel-controls{display:grid;grid-template-columns:1fr}
.rel-controls label{min-width:0}
.rel-count{padding-bottom:0}
}
@media print{
:root{color-scheme:light;--bg:#fff;--surface:#fff;--surface-2:#f2f3f5;--line:#d5d8dd;
--line-2:#b8bcc3;--ink:#000;--ink-2:#222;--muted:#555;--faint:#777;--accent:#2F8677;
--origin:#2F8677;--metadata:#3E6F9E;--activity:#8E6E2E;--alert:#B5563A}
body{font-size:10.5px}
.nav,.mast-actions,.copy,.chips,.tabs,.chev,a.card:after{display:none!important}
.file>summary{cursor:default}
details.file:not([open])>*:not(summary){display:block}
.js .pane,.pane{display:block!important}
.pane:before{display:block}
section{break-inside:avoid-page;padding:22px 0 6px}
.file,.conf,.find,.card,tr{break-inside:avoid}
thead{display:table-header-group}
a{color:inherit}
}
"""

_SCRIPT = """
(function () {
  var root = document.documentElement;
  root.classList.add('js');
  var each = function (list, visit) { Array.prototype.forEach.call(list, visit); };
  var one = function (selector) { return document.querySelector(selector); };
  var all = function (selector) { return document.querySelectorAll(selector); };

  var theme = one('#theme');
  function wear(name) {
    root.setAttribute('data-theme', name);
    theme.textContent = name === 'light' ? '\\u25D1' : '\\u25D0';
    theme.title = name === 'light' ? 'Dark theme' : 'Light theme';
    theme.setAttribute('aria-label', theme.title);
    try { localStorage.setItem('filegrail-theme', name); } catch (error) { /* private mode */ }
  }
  if (theme) {
    var kept = null;
    try { kept = localStorage.getItem('filegrail-theme'); } catch (error) { kept = null; }
    wear(kept === 'light' ? 'light' : 'dark');
    theme.addEventListener('click', function () {
      wear(root.getAttribute('data-theme') === 'light' ? 'dark' : 'light');
    });
  }
  var printer = one('#print');
  if (printer) { printer.addEventListener('click', function () { window.print(); }); }

  each(all('[data-expand]'), function (button) {
    button.addEventListener('click', function () {
      var held = button.closest('section');
      var blocks = held ? held.querySelectorAll('details') : [];
      var opening = Array.prototype.some.call(blocks, function (block) { return !block.open; });
      each(blocks, function (block) { block.open = opening; });
      button.textContent = (opening ? '\\u229F Collapse' : '\\u229E Expand') + ' all';
    });
  });

  document.addEventListener('click', function (event) {
    var button = event.target.closest ? event.target.closest('button.copy') : null;
    if (!button) { return; }
    var value = button.previousElementSibling ? button.previousElementSibling.textContent : '';
    function done(mark) {
      button.textContent = mark;
      button.classList.add('ok');
      setTimeout(function () {
        button.textContent = '\\u29C9';
        button.classList.remove('ok');
      }, 1000);
    }
    function fallback() {
      var area = document.createElement('textarea');
      area.value = value;
      document.body.appendChild(area);
      area.select();
      var copied = false;
      try { copied = document.execCommand('copy'); } catch (error) { copied = false; }
      document.body.removeChild(area);
      done(copied ? '\\u2713' : '\\u2717');
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(value).then(function () { done('\\u2713'); }, fallback);
    } else {
      fallback();
    }
  });

  var rows = Array.prototype.slice.call(all('#index tbody tr'));
  var counted = one('#shown');
  function filter(wanted) {
    each(all('.chip'), function (chip) {
      chip.classList.toggle('on', chip.dataset.filter === wanted);
    });
    var left = 0;
    rows.forEach(function (row) {
      var keep = wanted === 'all' || (row.dataset.f || '').split(' ').indexOf(wanted) !== -1;
      row.hidden = !keep;
      if (keep) { left += 1; }
    });
    if (counted) { counted.textContent = left; }
  }
  document.addEventListener('click', function (event) {
    if (!event.target.closest) { return; }
    var chip = event.target.closest('[data-filter]');
    if (chip) { filter(chip.dataset.filter); }
  });

  var relationshipRows = Array.prototype.slice.call(all('#relationship-table tbody tr'));
  var relationshipNode = one('#relationship-node');
  var relationshipCount = one('#relationship-shown');
  var relationshipKind = 'all';
  function filterRelationships() {
    var node = relationshipNode ? relationshipNode.value : '';
    var left = 0;
    relationshipRows.forEach(function (row) {
      var touches = !node || row.dataset.source === node || row.dataset.target === node;
      var ofKind = relationshipKind === 'all' || row.dataset.kind === relationshipKind;
      row.hidden = !(touches && ofKind);
      if (!row.hidden) { left += 1; }
    });
    each(all('[data-rel-kind]'), function (button) {
      var chosen = button.dataset.relKind === relationshipKind;
      button.classList.toggle('on', chosen);
      button.setAttribute('aria-pressed', chosen ? 'true' : 'false');
    });
    if (relationshipCount) {
      relationshipCount.textContent = left + (left === 1 ? ' relationship' : ' relationships');
    }
  }
  if (relationshipNode) {
    relationshipNode.addEventListener('change', filterRelationships);
  }
  each(all('[data-rel-kind]'), function (button) {
    button.addEventListener('click', function () {
      relationshipKind = button.dataset.relKind;
      filterRelationships();
    });
  });
  document.addEventListener('click', function (event) {
    if (!event.target.closest || !relationshipNode) { return; }
    var focus = event.target.closest('[data-rel-focus]');
    if (!focus) { return; }
    relationshipNode.value = focus.dataset.relFocus;
    relationshipKind = 'all';
    filterRelationships();
    relationshipNode.focus();
  });
  filterRelationships();

  function show(name) {
    each(all('.tabs button'), function (tab) {
      var chosen = tab.dataset.panel === name;
      tab.classList.toggle('on', chosen);
      tab.setAttribute('aria-selected', chosen ? 'true' : 'false');
    });
    each(all('.pane'), function (pane) { pane.classList.toggle('on', pane.id === name); });
  }
  each(all('.tabs button'), function (tab) {
    tab.addEventListener('click', function () { show(tab.dataset.panel); });
  });

  each(all('.tbl th[data-sort]'), function (head) {
    head.tabIndex = 0;
    function sort() {
      var table = head.closest('table');
      var body = table.tBodies[0];
      var column = Array.prototype.indexOf.call(head.parentNode.children, head);
      var numeric = head.dataset.sort === 'num';
      var rising = head.dataset.dir !== 'asc';
      each(table.querySelectorAll('th'), function (other) {
        delete other.dataset.dir;
        var arrow = other.querySelector('.dir');
        if (arrow) { arrow.remove(); }
      });
      head.dataset.dir = rising ? 'asc' : 'desc';
      head.insertAdjacentHTML('beforeend',
        '<span class="dir">' + (rising ? '\\u25B2' : '\\u25BC') + '</span>');
      function key(row) {
        var cell = row.children[column];
        if (!cell) { return numeric ? 0 : ''; }
        if (numeric) { return parseFloat(cell.dataset.value || 0) || 0; }
        return cell.textContent.trim().toLowerCase();
      }
      Array.prototype.slice.call(body.rows).sort(function (a, b) {
        var x = key(a), y = key(b);
        var order = numeric
          ? x - y
          : String(x).localeCompare(String(y), undefined, {numeric: true});
        return rising ? order : -order;
      }).forEach(function (row) { body.appendChild(row); });
    }
    head.addEventListener('click', sort);
    head.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); sort(); }
    });
  });

  var box = one('#search');
  var hits = one('#hits');
  function searchable() {
    return rows.concat(
      Array.prototype.slice.call(all('.find')),
      Array.prototype.slice.call(all('.conf')),
      Array.prototype.slice.call(all('.rec')),
      Array.prototype.slice.call(all('.pivot')),
      Array.prototype.slice.call(all('.relationship'))
    );
  }
  if (box) {
    box.addEventListener('input', function () {
      var wanted = box.value.trim().toLowerCase();
      var found = 0;
      var pane = null;
      if (wanted && relationshipNode) {
        relationshipNode.value = '';
        relationshipKind = 'all';
        filterRelationships();
      }
      searchable().forEach(function (item) {
        item.classList.remove('hit');
        if (!wanted) { return; }
        if (item.textContent.toLowerCase().indexOf(wanted) === -1) { return; }
        item.classList.add('hit');
        found += 1;
        var block = item.closest('details');
        if (block) { block.open = true; }
        var holder = item.closest('.pane');
        if (holder && !pane) { pane = holder.id; }
      });
      if (pane) { show(pane); }
      if (hits) { hits.textContent = wanted ? found + ' hits' : ''; }
      if (!wanted) { filter('all'); return; }
      var left = 0;
      rows.forEach(function (row) {
        row.hidden = !row.classList.contains('hit');
        if (!row.hidden) { left += 1; }
      });
      if (counted) { counted.textContent = left; }
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === '/' && document.activeElement !== box) {
        event.preventDefault();
        box.focus();
      }
      if (event.key === 'Escape' && document.activeElement === box) {
        box.value = '';
        box.dispatchEvent(new Event('input'));
        box.blur();
      }
    });
  }

  var links = Array.prototype.slice.call(all('.nav a[href^="#"]'));
  if (window.IntersectionObserver) {
    var watch = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) { return; }
        links.forEach(function (link) {
          link.classList.toggle('on', link.getAttribute('href') === '#' + entry.target.id);
        });
      });
    }, {rootMargin: '-45% 0px -50% 0px'});
    links.forEach(function (link) {
      var section = document.getElementById(link.getAttribute('href').slice(1));
      if (section) { watch.observe(section); }
    });
  }

  var top = document.getElementById('top');
  var bar = document.querySelector('.nav');
  if (top && bar && window.IntersectionObserver) {
    new IntersectionObserver(function (entries) {
      bar.classList.toggle('scrolled', !entries[0].isIntersecting);
    }, {threshold: 0}).observe(top);
  }

  function opened() {
    if (!location.hash) { return; }
    var target = document.getElementById(location.hash.slice(1));
    if (!target) { return; }
    var block = target.closest('details');
    if (block) { block.open = true; }
    var holder = target.closest('.pane');
    if (holder) { show(holder.id); }
  }
  window.addEventListener('hashchange', opened);
  opened();
})();
"""

#: Section key, the heading it prints, and the short word the nav gives it.
_SECTIONS = (
    ("summary", "Summary", "Summary"),
    ("findings", "Key findings", "Findings"),
    ("files", "Files", "Files"),
    ("relationships", "Relationships", "Related"),
    ("pivots", "Investigative pivots", "Pivots"),
    ("detail", "File detail", "Detail"),
    ("coverage", "Evidence coverage", "Coverage"),
    ("conflicts", "Conflicts", "Conflicts"),
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
    output: Path | None = None,
    now: datetime | None = None,
) -> str:
    """The whole page. A section with nothing in it is not written."""
    files = {entry.record.path: entry for entry in case.files}
    moment = (now or datetime.now().astimezone()).strftime("%Y-%m-%d %H:%M %Z").strip()
    detailed = {entry.record.path for entry in case.files if _wants_detail(entry, verbose)}
    panes = (
        {kind for kind, _count in case.pivots.by_type}
        if case.pivots is not None and identifiers is not None and case.pivots.total
        else set()
    )
    records = [entry.record for entry in case.files]
    graph = build_graph(records, identifiers or [])
    relationship_count = len(graph.relationships)
    sections = {
        "summary": _summary(case, relationship_count),
        "findings": _findings(case, files),
        "coverage": _coverage(case, unsearched),
        "conflicts": _conflicts(case, files, detailed),
        "files": _files(case, detailed, panes),
        "relationships": _relationships(graph, files),
        "pivots": _pivots(case, files, identifiers),
        "detail": _details(case, files, detailed, verbose=verbose),
    }
    counted = _counts(case, detailed, relationship_count)
    present = [(key, title, short) for key, title, short in _SECTIONS if sections[key]]

    options = [
        ("--content", content),
        ("--pivots", identifiers is not None),
        ("--redact", redacted),
        ("--verbose", verbose),
    ]
    enabled = " ".join(name for name, on in options if on) or "none"
    facts = [("target", str(case.root))]
    if home:
        facts.append(("profile", f"{home} · external"))
    contents = inventory(records)
    facts.append(("scanned", f"{moment} · {len(records):,} files · {_size(contents.size)}"))
    facts.append(("options", enabled))
    if output is not None:
        facts.append(("report", str(output)))

    head = [
        "<!doctype html>",
        '<html lang="en" data-theme="dark">',
        "<head>",
        '<meta charset="utf-8">',
        f'<meta http-equiv="Content-Security-Policy" content="{POLICY}">',
        '<meta name="referrer" content="no-referrer">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="color-scheme" content="dark light">',
        f"<title>filegrail · {_e(Path(case.root).name or str(case.root))}</title>",
        _FAVICON,
        f"<style>{_STYLE}</style>",
        "</head>",
        "<body>",
    ]
    masthead = [
        '<header class="mast" id="top">',
        _MARK,
        '<div class="who">',
        '<div class="word">filegrail '
        f"<small>v{_e(__version__)} · investigation report</small></div>",
        '<div class="tag">Trace origins · Extract metadata · Discover pivots</div>',
        "</div>",
        '<div class="mast-actions">',
        '<button class="btn" id="print" type="button">⎙ Print / PDF</button>',
        '<button class="btn icon" id="theme" type="button" '
        'title="Light theme" aria-label="Light theme">◐</button>',
        "</div>",
        _fields(facts, css="facts", copy=frozenset({"target", "profile", "report"})),
        "</header>",
    ]
    links = "".join(
        f'<a href="#{key}">{_e(short)}'
        + (f" <b>{counted[key]}</b>" if counted.get(key) else "")
        + "</a>"
        for key, _title, short in present
    )
    upwards = (
        '<a class="home" href="#top" title="Back to the top" '
        f'aria-label="Back to the top">{_MARK}</a>'
    )
    nav = [
        f'<nav class="nav">{upwards}{links}<span class="sp"></span>',
        '<label class="search"><input id="search" type="search" '
        'placeholder="search paths, values, fields" aria-label="Search the report" '
        'autocomplete="off" spellcheck="false">'
        '<span class="hits" id="hits"></span><kbd>/</kbd></label>',
        "</nav>",
    ]
    body = ["<main>"]
    for key, title, _short in present:
        body.append(
            _section(
                key,
                title,
                sections[key],
                _note(key, case, detailed, relationship_count),
            )
        )
    if filtered:
        said = "No file matched" if not case.files else "Limited to"
        body.append(f'<p class="note">{_e(said)} {_e(filtered)}.</p>')
    body.append("</main>")
    footer = [
        "<footer>",
        f"<span>filegrail v{_e(__version__)} · Apache-2.0</span>",
        f"<span>generated {_e(moment)}</span>",
        "<span>this page makes no network requests</span>",
        "</footer>",
    ]
    tail = [f"<script>{_SCRIPT}</script>", "</body>", "</html>"]
    return "\n".join(head + masthead + nav + body + footer + tail) + "\n"


# --- the frame -------------------------------------------------------------------


def _counts(case: Case, detailed: set[str], relationship_count: int) -> dict[str, str]:
    """The number the nav prints beside a section, where a number helps."""
    said = {
        "findings": f"{len(case.findings)}" if case.findings else "",
        "files": f"{len(case.files)}" if case.files else "",
        "detail": f"{len(detailed)}" if detailed else "",
        "conflicts": f"{len(case.conflicts)}" if case.conflicts else "",
        "relationships": f"{relationship_count}" if relationship_count else "",
    }
    if case.pivots is not None and case.pivots.total:
        said["pivots"] = f"{case.pivots.total}"
    return said


def _note(key: str, case: Case, detailed: set[str], relationship_count: int) -> str:
    """What the section heading says beside its name: the count, and what it counts."""
    if key == "findings" and case.findings:
        return f"{len(case.findings)}"
    if key == "files" and case.files:
        return f'{len(case.files):,} <b>· showing <span id="shown">{len(case.files):,}</span></b>'
    if key == "detail" and detailed:
        return f"{len(detailed):,} <b>· files that need it</b>"
    if key == "conflicts" and case.conflicts:
        return f"{len(case.conflicts)}"
    if key == "relationships" and relationship_count:
        return f"{relationship_count:,}"
    if key == "pivots" and case.pivots is not None:
        return f"{case.pivots.total:,} <b>· {case.pivots.across:,} in more than one file</b>"
    if key == "coverage":
        stores = [source for source in case.coverage if source.store]
        if stores:
            found = sum(1 for source in stores if source.state == "found")
            return f"{found} <b>of {len(stores)} trace stores</b>"
    return ""


def _section(key: str, title: str, body: str, note: str) -> str:
    """A section, with the control for what it holds only where there is something to open."""
    counted = f'<span class="n">{note}</span>' if note else ""
    tools = (
        '<button class="btn" type="button" data-expand>⊞ Expand all</button>'
        if "<details" in body
        else ""
    )
    return (
        f'<section id="{key}"><div class="h"><h2>{_e(title)}</h2>{counted}{tools}</div>'
        f"{body}</section>"
    )


# --- pieces ----------------------------------------------------------------------


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def _anchor(ref: str) -> str:
    """The id a report number is found under: `#001` is `file-001`."""
    return f"file-{ref[1:]}" if ref.startswith("#") else ref


def _link(ref: str) -> str:
    return f'<a href="#{_anchor(ref)}">{_e(ref)}</a>'


def _fields(
    pairs: list[tuple[str, str]],
    css: str = "fields",
    copy: bool | frozenset[str] = False,
    plain: frozenset[str] = frozenset(),
) -> str:
    """Labels and their values. Values `copy` names - or all but `plain` - get a copy button."""
    rows = []
    for label, value in pairs:
        wanted = (copy is True and label not in plain) or (
            isinstance(copy, frozenset) and label in copy
        )
        rows.append(f"<dt>{_e(label)}</dt><dd>{_value(value) if wanted else _e(value)}</dd>")
    return f'<dl class="{css}">{"".join(rows)}</dl>'


def _value(value: str) -> str:
    """A value and a button that copies it: the text shown, never a second copy of it."""
    return (
        f'<span class="v">{_e(value)}</span>'
        '<button class="copy" type="button" title="copy" aria-label="copy">⧉</button>'
    )


def _name(entry: CaseFile) -> str:
    return Path(entry.record.path).name


def _file_link(entry: CaseFile) -> str:
    """The number and the name as one link: four characters make a poor target."""
    return f'<a href="#{_anchor(entry.ref)}">{_e(entry.ref)} {_e(_name(entry))}</a>'


def _match(found: EvidenceRecord) -> str:
    """The basis a record was tied to the file by, and whether it is an exact one."""
    strong = " strong" if found.matched_by in _STRONG else ""
    return f'<span class="pill match{strong}">{_e(found.matched_by)}</span>'


def _card(
    value: str,
    label: str,
    said: str = "",
    section: str | None = None,
    chosen: str = "",
    css: str = "",
) -> str:
    """One number in the summary, and what it opens when it opens something."""
    inner = f'<span class="v">{value}</span><span class="k">{_e(label)}</span>'
    if said:
        inner += f'<span class="s">{_e(said)}</span>'
    classes = f"card {css}".strip()
    if section is None:
        return f'<div class="{classes}">{inner}</div>'
    picked = f' data-filter="{chosen}"' if chosen else ""
    return f'<a class="{classes}" href="#{section}"{picked}>{inner}</a>'


def _sources(entries: list[CaseFile], name: str) -> str:
    """What is behind a category card: the sources that account for most of it."""
    counted: Counter[str] = Counter()
    for entry in entries:
        counted.update(entry.found[name])
    return " · ".join(label for label, _times in counted.most_common(3))


def _summary(case: Case, relationship_count: int) -> str:
    if not case.files:
        return ""
    records = [entry.record for entry in case.files]
    contents = inventory(records)
    holding = {name: [entry for entry in case.files if entry.found[name]] for name in CATEGORIES}
    review = [entry for entry in case.files if entry.state == REVIEW]
    quiet = [entry for entry in case.files if entry.state == NOTHING]
    fields = sum(len(conflict.differences) for conflict in case.conflicts)
    files = "files" if case.files else None

    cards = [
        _card(
            f"{len(records):,}",
            "files scanned",
            f"{len(contents.types):,} types · {_size(contents.size)}",
            files,
            "all",
        )
    ]
    for name in CATEGORIES:
        entries = holding[name]
        if not entries:
            continue
        cards.append(
            _card(f"{len(entries):,}", f"with {name}", _sources(entries, name), files, name, name)
        )
    if review:
        said = f"{len(case.conflicts)} conflicts · {fields} fields" if case.conflicts else ""
        cards.append(_card(f"{len(review):,}", "need a second look", said, files, "flag", "alert"))
    if quiet:
        cards.append(
            _card(
                f"{len(quiet):,}",
                "no evidence found",
                "see coverage before reading as absence",
                files,
                "none",
            )
        )
    if relationship_count:
        cards.append(
            _card(
                f"{relationship_count:,}",
                "relationships",
                "evidence-backed graph edges",
                "relationships",
            )
        )
    if case.pivots is not None and case.pivots.total:
        said = f"{case.pivots.across:,} in more than one file"
        if case.pivots.cross_corpus:
            said += f" · {case.pivots.cross_corpus:,} in both corpora"
        cards.append(_card(f"{case.pivots.total:,}", "pivots", said, "pivots", "", "accent"))
    stores = [source for source in case.coverage if source.store]
    if stores:
        found = sum(1 for source in stores if source.state == "found")
        said = f"history begins {case.begins}" if case.begins else ""
        cards.append(
            _card(
                f'{found}<span class="of">/{len(stores)}</span>',
                "trace stores found",
                said,
                "coverage",
            )
        )
    legend = (
        '<div class="legend">'
        '<span class="cat origin">origin · how it got here</span>'
        '<span class="cat metadata">metadata · what it says about itself</span>'
        '<span class="cat activity">activity · what happened to it here</span>'
        '<span><span class="flag">!</span> wants a second look</span>'
        "</div>"
    )
    return f'<div class="cards">{"".join(cards)}</div>{legend}'


def _findings(case: Case, files: dict[str, CaseFile]) -> str:
    return "".join(_finding(case, finding, files) for finding in case.findings)


def _finding(case: Case, finding: Finding, files: dict[str, CaseFile]) -> str:
    warn = " warn" if finding.notable else ""
    facts = [(label, value) for label, value in finding.facts]
    if finding.kind in _PER_FILE:
        facts = [fact for fact in facts if fact[0] != "files"]
    parts = [
        f'<div class="find" id="{finding.ref}">',
        f'<a class="fid" href="#{finding.ref}">{finding.ref}</a><div>',
        f'<div class="t{warn}">{_e(finding.title)}</div>',
    ]
    if facts:
        parts.append(_fields([(_capital(label), value) for label, value in facts]))
    if finding.kind in _PER_FILE:
        for item in finding.items:
            entry = files[item.path]
            pairs = [(_capital(label), value) for label, value in item.facts]
            parts.append(
                f'<div class="files">{_file_link(entry)}</div>{_fields(pairs)}'
                if pairs
                else f'<div class="files">{_file_link(entry)}</div>'
            )
    elif finding.items:
        listed = " ".join(_file_link(files[item.path]) for item in finding.items)
        if finding.kind in _LISTED:
            parts.append(f'<div class="files">{listed}</div>')
        else:
            parts.append(
                f"<details><summary>{len(finding.items)} files</summary>"
                f'<div class="files">{listed}</div></details>'
            )
    if finding.kind == "no-trace":
        said = "This does not mean the files were never downloaded or transferred."
        if case.begins:
            said += f" Available trace history begins on {case.begins}."
        parts.append(f'<div class="note">{_e(said)}</div>')
    if finding.see:
        target = "conflicts" if finding.see == "CONFLICTS" else "coverage"
        parts.append(
            f'<div class="note">See <a href="#{target}">{_e(finding.see.lower())}</a>.</div>'
        )
    parts.append("</div></div>")
    return "".join(parts)


def _files(case: Case, detailed: set[str], panes: set[str]) -> str:
    if not case.files:
        return ""
    kinds = {finding.ref: finding.kind for finding in case.findings}
    rows = []
    for entry in case.files:
        record = entry.record
        marks = ["flag"] if entry.state == REVIEW else []
        marks += [name for name in CATEGORIES if entry.found[name]]
        if entry.state == NOTHING:
            marks.append("none")
        number = _e(entry.ref)
        opens = (
            f'<a href="#detail-{entry.ref[1:]}">{number}</a>' if record.path in detailed else number
        )
        flag = '<span class="flag">!</span>' if entry.state == REVIEW else ""
        dots = '<span class="dots" title="origin · metadata · activity">' + "".join(
            f'<i class="{name[0]}"></i>' if entry.found[name] else "<i></i>" for name in CATEGORIES
        )
        origin = record.origin
        arrived = (
            f'<span class="cat origin">{_e(named(origin))}</span> {_match(origin)}'
            if origin is not None
            else '<span class="dim">·</span>'
        )
        rows.append(
            f'<tr id="{_anchor(entry.ref)}" data-f="{" ".join(marks)}">'
            f'<td class="id">{opens}</td><td>{flag}</td>'
            f'<td class="path">{_value(_relative(record.path, case.root))}</td>'
            f"<td>{_e(_format(record.path))}</td>"
            f'<td class="num" data-value="{record.size}">{_e(_size(record.size))}</td>'
            f'<td class="dim">{_e(_stamp(shown(record.mtime)))}</td>'
            f"<td>{dots}</span></td><td>{arrived}</td>"
            f"<td>{_found_in(entry, kinds, panes)}</td></tr>"
        )
    return (
        f'<div class="chips">{_chips(case)}</div>'
        '<div class="wrap"><table class="tbl index" id="index"><thead><tr>'
        '<th data-sort="text">#</th><th></th><th data-sort="text">path</th>'
        '<th data-sort="text">type</th><th data-sort="num" class="num">size</th>'
        '<th data-sort="text">modified</th><th>evidence</th>'
        '<th data-sort="text">origin</th>'
        '<th data-sort="text">findings &amp; pivots</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _chips(case: Case) -> str:
    """The filters over the file index, each with what it would leave."""
    counted = [("all", "all", len(case.files))]
    review = sum(1 for entry in case.files if entry.state == REVIEW)
    if review:
        counted.append(("flag", "second look", review))
    for name in CATEGORIES:
        held = sum(1 for entry in case.files if entry.found[name])
        if held:
            counted.append((name, name, held))
    quiet = sum(1 for entry in case.files if entry.state == NOTHING)
    if quiet:
        counted.append(("none", "no evidence", quiet))
    return "".join(
        f'<button type="button" class="chip{" on" if key == "all" else ""}" '
        f'data-filter="{key}">{_e(label)} <b>{times:,}</b></button>'
        for key, label, times in counted
    )


def _found_in(entry: CaseFile, kinds: dict[str, str], panes: set[str]) -> str:
    """The findings and conflicts a file is named in, then the pivot types found in it.

    Each of them leads somewhere: a finding to its paragraph, a pivot type to
    the tab that lists every pivot of that type and the files it was found in.
    """
    said = [_link(ref) for ref in entry.findings if kinds[ref] != "no-trace"]
    said += [_link(ref) for ref in entry.conflicts]
    found = [
        f'<a href="#pivots-type-{kind}">{_e(_type_name(kind))}</a>'
        if kind in panes
        else _e(_type_name(kind))
        for kind in entry.pivots
    ]
    pivots = f'<span class="dim">{" · ".join(found)}</span>' if found else ""
    return " ".join(said + ([pivots] if pivots else []))


def _relationships(graph: Graph, files: dict[str, CaseFile]) -> str:
    """An offline explorer over the same graph JSON and exports use."""
    if not graph.relationships:
        return ""

    nodes = {node.id: node for node in graph.nodes}
    connected = {edge.source for edge in graph.relationships} | {
        edge.target for edge in graph.relationships
    }
    kinds = Counter(edge.kind for edge in graph.relationships)
    chips = ['<button type="button" class="chip on" data-rel-kind="all">all</button>']
    chips.extend(
        f'<button type="button" class="chip" data-rel-kind="{_e(kind)}">'
        f"{_e(kind)} <b>{count:,}</b></button>"
        for kind, count in sorted(kinds.items())
    )

    rows = []
    ordered = sorted(
        graph.relationships,
        key=lambda edge: (edge.kind.casefold(), edge.source, edge.target),
    )
    for edge in ordered:
        source = nodes[edge.source]
        target = nodes[edge.target]
        occurrence = "occurrence" if edge.count == 1 else "occurrences"
        often = f'<span class="dim">{edge.count:,} {occurrence}</span>'
        rows.append(
            f'<tr class="relationship" data-source="{_e(edge.source)}" '
            f'data-target="{_e(edge.target)}" data-kind="{_e(edge.kind)}">'
            f"<td>{_relationship_node(source, files)}</td>"
            '<td class="arrow" aria-label="points to">→</td>'
            f'<td class="kind">{_e(edge.kind)}{often}</td>'
            f"<td>{_relationship_node(target, files)}</td>"
            f"<td>{_relationship_evidence(edge)}</td></tr>"
        )

    controls = (
        '<div class="rel-controls"><label for="relationship-node">Focus node'
        '<select id="relationship-node"><option value="">All connected nodes</option>'
        f"{_relationship_options(graph, connected, files)}</select></label>"
        f'<span class="rel-count" id="relationship-shown">{len(rows):,} relationships</span>'
        "</div>"
        f'<div class="rel-kinds" aria-label="Relationship type filters">{"".join(chips)}</div>'
    )
    table = (
        '<div class="wrap"><table class="tbl relationships" id="relationship-table">'
        '<thead><tr><th data-sort="text">source</th><th></th>'
        '<th data-sort="text">relationship</th><th data-sort="text">target</th>'
        f"<th>evidence</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )
    return controls + table


def _relationship_options(graph: Graph, connected: set[str], files: dict[str, CaseFile]) -> str:
    degrees = Counter(
        node_id for edge in graph.relationships for node_id in (edge.source, edge.target)
    )
    groups: dict[str, list[Node]] = {}
    for node in graph.nodes:
        if node.id in connected:
            groups.setdefault(node.type, []).append(node)

    order = {"file": 0, "person": 1, "device": 2, "camera_model": 3}
    rendered = []
    for kind, nodes in sorted(groups.items(), key=lambda item: (order.get(item[0], 4), item[0])):
        options = []
        for node in sorted(nodes, key=lambda item: (-degrees[item.id], item.value.casefold())):
            value = _relationship_option_label(node, files)
            options.append(
                f'<option value="{_e(node.id)}">{_e(value)} · {degrees[node.id]:,}</option>'
            )
        label = {
            "camera_model": "camera models",
            "device": "camera bodies",
            "file": "files",
            "person": "people",
        }.get(kind, _type_name(kind).lower())
        rendered.append(f'<optgroup label="{_e(label)}">{"".join(options)}</optgroup>')
    return "".join(rendered)


def _relationship_option_label(node: Node, files: dict[str, CaseFile]) -> str:
    if node.type == "file" and node.value in files:
        entry = files[node.value]
        return f"{entry.ref} {_name(entry)}"
    return node.value


def _node_type(kind: str) -> str:
    return {
        "bic": "BIC",
        "camera_model": "camera model",
        "cve": "CVE",
        "cwe": "CWE",
        "device": "camera body",
        "email": "email",
        "file": "file",
        "ghsa": "GHSA",
        "ipv4": "IPv4",
        "ipv6": "IPv6",
        "md5": "MD5",
        "person": "person",
        "sha1": "SHA-1",
        "sha256": "SHA-256",
        "sha512": "SHA-512",
        "url": "URL",
    }.get(kind, kind.replace("_", " "))


def _relationship_node(node: Node, files: dict[str, CaseFile]) -> str:
    if node.type == "file" and node.value in files:
        value = _file_link(files[node.value])
    else:
        value = _value(node.value)
    focus = (
        f'<button class="rel-focus" type="button" data-rel-focus="{_e(node.id)}" '
        f'title="Focus this node" aria-label="Focus {_e(node.value)}">◎</button>'
    )
    return (
        '<div class="rel-node">'
        f'<span class="pill">{_e(_node_type(node.type))}</span>{value}{focus}</div>'
    )


def _relationship_evidence(edge: Relationship) -> str:
    proofs = []
    for proof in edge.evidence:
        facts = [
            ("source", proof.source),
            ("place", proof.place),
            ("corpus", proof.corpus),
        ]
        if proof.category is not None:
            facts.append(("category", proof.category))
        if proof.match is not None:
            facts.append(("match", proof.match))
        if proof.at is not None:
            facts.append(("time", proof.at))
        if proof.count != 1:
            facts.append(("occurrences", f"{proof.count:,}"))
        proofs.append(f'<div class="rel-proof">{_fields(facts)}</div>')
    count = len(proofs)
    label = "evidence item" if count == 1 else "evidence items"
    return f"<details><summary>{count:,} {label}</summary>{''.join(proofs)}</details>"


def _pivots(case: Case, files: dict[str, CaseFile], identifiers: list[Identifier] | None) -> str:
    """Every pivot, one tab a type, each with the files it was found in and where."""
    pivots = case.pivots
    if pivots is None or not pivots.total or identifiers is None:
        return ""
    kinds: dict[str, list[Identifier]] = {}
    for entry in identifiers:
        kinds.setdefault(entry.type, []).append(entry)
    refs = {f"{entry.type}\0{entry.normalized}": ref for ref, entry in pivots.shared}
    across = sorted(
        (entry for entry in identifiers if entry.files > 1),
        key=lambda entry: (-entry.files, -entry.count, entry.type, entry.normalized),
    )

    panels: list[tuple[str, str, int, str]] = []
    if across:
        table = _pivot_table(across, files, refs, across=True)
        panels.append(("pivots-across", "Across files", len(across), table))
    if pivots.dense:
        panels.append(
            ("pivots-dense", "High-density files", len(pivots.dense), _dense(pivots, files))
        )
    for kind, count in pivots.by_type:
        table = _pivot_table(kinds[kind], files, refs, across=False)
        panels.append((f"pivots-type-{kind}", _type_name(kind), count, table))

    tabs = "".join(
        f'<button type="button" role="tab" data-panel="{key}" '
        f'class="{"on" if number == 0 else ""}" '
        f'aria-selected="{"true" if number == 0 else "false"}">'
        f"{_e(label)} <b>{count:,}</b></button>"
        for number, (key, label, count, _table) in enumerate(panels)
    )
    shown_panels = "".join(
        f'<div class="pane{" on" if number == 0 else ""}" id="{key}" role="tabpanel" '
        f'data-label="{_e(label)}">{table}</div>'
        for number, (key, label, _count, table) in enumerate(panels)
    )
    return f'<div class="tabs" role="tablist">{tabs}</div>{shown_panels}'


def _pivot_table(
    entries: list[Identifier], files: dict[str, CaseFile], refs: dict[str, str], *, across: bool
) -> str:
    rows = []
    for entry in entries:
        ref = refs.get(f"{entry.type}\0{entry.normalized}")
        holders = sorted(
            entry.holders.items(),
            key=lambda pair: (-pair[1], files[pair[0]].ref if pair[0] in files else pair[0]),
        )
        named_here = [_holder(files, path, times) for path, times in holders[:_HOLDERS]]
        found_in = " ".join(named_here)
        left = len(holders) - len(named_here)
        if left:
            rest = " ".join(_holder(files, path, times) for path, times in holders[_HOLDERS:])
            found_in += f"<details><summary>+{left:,} more</summary>{rest}</details>"
        places = _places(entry.where[:_SAMPLE])
        opening = f'<tr class="pivot" id="{ref}">' if ref else '<tr class="pivot">'
        leading = (
            f'<td class="id">{_e(ref or "")}</td><td>{_e(_type_name(entry.type))}</td>'
            if across
            else ""
        )
        rows.append(
            opening + leading + f'<td class="val">{_value(entry.value)}</td>'
            f'<td class="num" data-value="{entry.files}">{entry.files:,}</td>'
            f'<td class="num" data-value="{entry.count}">{entry.count:,}</td>'
            f'<td class="where">{places}</td><td class="found">{found_in}</td></tr>'
        )
    heads = '<th data-sort="text">#</th><th data-sort="text">type</th>' if across else ""
    return (
        f'<div class="wrap"><table class="tbl pivots"><thead><tr>{heads}'
        '<th data-sort="text">value</th><th data-sort="num" class="num">files</th>'
        '<th data-sort="num" class="num">times</th><th>where (sample)</th>'
        f"<th>found in</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _places(sample: list[str]) -> str:
    """Where a value was found, one line a file and source.

    A value sitting five times in one file says that file's name once and then
    the five spots inside it, rather than five lines that differ by a number.
    """
    grouped: dict[tuple[str, str], list[str]] = {}
    for place in sample:
        held, _, rest = place.partition(PLACE)
        source, _, spot = rest.partition(PLACE)
        grouped.setdefault((held, source), []).append(spot)
    lines = []
    for (held, source), spots in grouped.items():
        said = PLACE.join(part for part in (held, source) if part)
        kept = [spot for spot in spots if spot]
        if kept:
            said += PLACE + _spots(kept)
        lines.append(_e(said))
    return "<br>".join(lines)


def _spots(spots: list[str]) -> str:
    """`lines 2, 3, 4` where the spots are numbered the same way, else as they are."""
    if len(spots) > 1:
        heads = {spot.rsplit(" ", 1)[0] for spot in spots}
        tails = [spot.rsplit(" ", 1)[-1] for spot in spots]
        head = heads.pop() if len(heads) == 1 else None
        if head and head.isalpha() and head.islower() and all(t.isdigit() for t in tails):
            return f"{head}s {', '.join(tails)}"
    return ", ".join(spots)


def _holder(files: dict[str, CaseFile], path: str, times: int) -> str:
    """A file a pivot was found in, as a link to it, and how often when more than once."""
    held = files.get(path)
    name = _file_link(held) if held else _e(Path(path).name)
    often = f" ×{times:,}" if times > 1 else ""
    return f'<span class="holder">{name}{often}</span>'


def _dense(pivots: Pivots, files: dict[str, CaseFile]) -> str:
    rows = []
    for dense in pivots.dense:
        held = files.get(dense.path)
        name = _file_link(held) if held else _e(dense.path)
        kinds = " · ".join(f"{_type_name(kind)} {count:,}" for kind, count in dense.by_type)
        rows.append(
            f'<tr class="pivot"><td class="path">{name}</td>'
            f'<td class="num" data-value="{dense.places}">{dense.places:,}</td>'
            f"<td>{_e(kinds)}</td></tr>"
        )
    return (
        '<div class="wrap"><table class="tbl"><thead><tr><th data-sort="text">file</th>'
        '<th data-sort="num" class="num">places</th><th>by type</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _wants_detail(entry: CaseFile, verbose: bool) -> bool:
    """A file gets a block of its own when there is something to read in it."""
    wanted = entry.state == REVIEW or entry.found[ORIGIN] or entry.found[ACTIVITY]
    return bool(wanted) or (verbose and entry.state != NOTHING)


def _details(case: Case, files: dict[str, CaseFile], detailed: set[str], *, verbose: bool) -> str:
    findings = {finding.ref: finding for finding in case.findings}
    conflicts = {conflict.ref: conflict for conflict in case.conflicts}
    parts = []
    for entry in case.files:
        if entry.record.path not in detailed:
            continue
        parts.append(_detail(case, entry, files, findings, conflicts, verbose=verbose))
    return "".join(parts)


def _detail(
    case: Case,
    entry: CaseFile,
    files: dict[str, CaseFile],
    findings: dict[str, Finding],
    conflicts: dict[str, Conflict],
    *,
    verbose: bool,
) -> str:
    record = entry.record
    body = []
    for name in CATEGORIES:
        held = [found for found in record.evidence if category(found) == name]
        if not held:
            body.append(
                f'<div class="rec silent"><span class="cat none">{_e(name)}</span>'
                f'<div><div class="note">{_e(_ABSENT[name])}</div></div></div>'
            )
            continue
        for found in held:
            facts = [
                (label, value)
                for label, value in _facts(found, name, verbose=verbose)
                if label != "Match"
            ]
            body.append(
                f'<div class="rec"><span class="cat {name}">{_e(name)}</span>'
                f'<div><div class="src">{_e(named(found))} {_match(found)}</div>'
                + (f'<div class="note">{_e(found.note)}</div>' if found.note else "")
                + "</div>"
                + (_fields(facts, copy=True) if facts else "")
                + "</div>"
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
            said += ": " + " · ".join(_file_link(other) for other in others)
        elif others:
            said += f": with {len(others)} other files"
        notes.append(said)
    if notes:
        body.append(
            '<div class="extra"><span class="k">notes</span><ul>'
            + "".join(f"<li>{note}</li>" for note in notes)
            + "</ul></div>"
        )
    flag = ' <span class="flag">!</span>' if entry.state == REVIEW else ""
    refs = " ".join(_link(ref) for ref in entry.findings + entry.conflicts)
    meta = f"{_e(_size(record.size))} · {_e(_format(record.path))}"
    review = " review" if entry.state == REVIEW else ""
    return (
        f'<details class="file{review}" id="detail-{entry.ref[1:]}"'
        f"{' open' if entry.state == REVIEW else ''}>"
        f'<summary><span class="id">{_e(entry.ref)}</span>'
        f'<span class="name">{_e(_relative(record.path, case.root))}{flag}</span>'
        f'<span class="meta">{meta} {refs}<span class="chev">›</span></span></summary>'
        f"{''.join(body)}</details>"
    )


def _coverage(case: Case, unsearched: Unsearched | None) -> str:
    missed = [(path, "could not be read") for path in (unsearched.unreadable if unsearched else [])]
    missed += [(path, "skipped by name") for path in (unsearched.by_name if unsearched else [])]
    if not case.coverage and not missed:
        return ""
    states = {"found": "origin", "readable": "origin", "partial": "activity"}
    rows = []
    for source in case.coverage:
        state = states.get(source.state, "none")
        rows.append(
            f'<tr><td class="path">{_e(source.name)}</td>'
            f'<td><span class="cat {state}">{_e(source.state)}</span></td>'
            f"<td>{_e(source.detail)}</td>"
            f'<td class="dim">{_e(source.since or "·")}</td></tr>'
        )
    for path, why in missed:
        rows.append(
            f'<tr><td class="path">{_e(_relative(path, case.root))}</td>'
            f'<td><span class="cat none">{_e(why)}</span></td>'
            f'<td class="dim">·</td><td class="dim">·</td></tr>'
        )
    table = (
        '<div class="wrap"><table class="tbl"><thead><tr><th data-sort="text">source</th>'
        '<th data-sort="text">state</th><th>coverage</th><th data-sort="text">horizon</th>'
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )
    if case.begins:
        said = f"Observable trace history begins on {case.begins}."
        return f'{table}<p class="note">{_e(said)}</p>'
    return table


def _conflicts(case: Case, files: dict[str, CaseFile], detailed: set[str]) -> str:
    return "".join(_conflict(conflict, files, detailed) for conflict in case.conflicts)


def _conflict(conflict: Conflict, files: dict[str, CaseFile], detailed: set[str]) -> str:
    entry = files[conflict.path]
    detail = f' <a href="#detail-{entry.ref[1:]}">detail</a>' if conflict.path in detailed else ""
    fields = " · ".join(difference.field for difference in conflict.differences)
    said = f"{' and '.join(conflict.sources) or 'Two records'} disagree on {fields}"
    parts = [
        f'<div class="conf" id="{conflict.ref}">',
        f'<a class="cid" href="#{conflict.ref}">{conflict.ref}</a><div>',
        f'<div class="t">{_file_link(entry)} · {_e(said)}{detail}</div>',
    ]
    for difference in conflict.differences:
        pair = "".join(
            f'<div><div class="src">{_e(source or "value")}</div>'
            f'<div class="v">{_value(value)}</div></div>'
            for source, value in difference.values
        )
        parts.append(
            f'<div class="field">{_e(difference.field)}</div><div class="pair">{pair}</div>'
        )
        if difference.delta:
            first = difference.values[0][0] or "the first"
            second = difference.values[-1][0] or "the second"
            parts.append(
                f'<div class="delta">{_e(f"{second} is {difference.delta} than {first}")}</div>'
            )
    parts.append("</div></div>")
    return "".join(parts)
