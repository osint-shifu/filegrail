"""The stylesheet of the HTML report, written into the page.

Kept apart from the renderer so the rules read as a stylesheet, and still
written inline: the report is one file that loads nothing.
"""

from __future__ import annotations

#: The light palette, applied when chosen and, until a choice is made, when
#: the system prefers it. Written once and placed twice.
LIGHT = """color-scheme:light;
--bg:#F4F5F6;--surface:#FFFFFF;--surface-2:#EEF0F2;--line:#DDE0E4;--line-2:#C9CDD3;
--ink:#0F1115;--ink-2:#2C3138;--muted:#5D646C;--faint:#8A9098;
--accent:#356282;--accent-ink:#FFFFFF;--accent-soft:rgba(53,98,130,.12);
--origin:#2F8677;--metadata:#5F58AD;--activity:#8E6E2E;--alert:#B5563A;
--alert-soft:rgba(181,86,58,.12)"""

STYLE = """
:root{color-scheme:dark;
--bg:#0F1115;--surface:#151920;--surface-2:#1B2027;--line:#262A31;--line-2:#333944;
--ink:#E6E8EB;--ink-2:#C3C8CE;--muted:#9AA1A9;--faint:#6B727B;
--accent:#6EA0C4;--accent-ink:#0F1115;--accent-soft:rgba(110,160,196,.14);
--origin:#5FA89A;--metadata:#A39BD9;--activity:#C9A66B;--alert:#D08770;
--alert-soft:rgba(208,135,112,.14);
--mono:"IBM Plex Mono","JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
--r:3px;--gutter:clamp(20px,4vw,64px);--nav:48px}
[data-theme=light]{%LIGHT%}
@media (prefers-color-scheme:light){:root:not([data-theme=dark]){%LIGHT%}}
*{box-sizing:border-box}
[hidden]{display:none!important}
html{scroll-padding-top:calc(var(--nav) + 24px);scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:13px/1.55 var(--mono);
font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased;text-wrap:pretty}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline;text-underline-offset:3px}
code{font:inherit}
button{font:inherit;color:inherit;background:none;border:0;padding:0;cursor:pointer}
::selection{background:var(--accent);color:var(--accent-ink)}

/* ── masthead ─────────────────────────────────────────────── */
.mast{padding:22px var(--gutter) 24px;border-bottom:1px solid var(--line)}
.mast .word{margin:0 0 16px;font-size:11px;font-weight:400;letter-spacing:.18em;
text-transform:uppercase;color:var(--muted)}
.mast .word small{font-size:inherit;color:var(--faint)}
.mast-body{display:grid;grid-template-columns:auto 1fr;gap:0 26px;align-items:stretch}
.mast-mark{display:flex;align-items:stretch}
.mast .mark{height:100%;width:auto;flex:none}
.mast .tag{display:none}
.facts{display:grid;grid-template-columns:auto 1fr;gap:6px 24px;justify-content:start;margin:0;
font-size:12px;align-content:center}
.facts dt{font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--faint)}
.facts dd{margin:0;color:var(--ink);overflow-wrap:anywhere}
.mast-actions{display:none;gap:6px;align-items:center;margin-left:8px;flex:none}
.js .mast-actions{display:flex}
.btn{display:inline-flex;align-items:center;gap:8px;height:30px;padding:0 12px;
border:1px solid var(--line-2);border-radius:var(--r);color:var(--ink-2);font-size:12px;
white-space:nowrap;background:var(--surface)}
.btn:hover{border-color:var(--accent);color:var(--ink)}
.btn.icon{width:30px;padding:0;justify-content:center}
.ic{width:14px;height:14px;fill:currentColor;flex:none;display:block}
.btn.icon .sun{display:none}
[data-theme=light] .btn.icon .sun{display:block}
[data-theme=light] .btn.icon .moon{display:none}

/* ── sticky nav ───────────────────────────────────────────── */
.nav{position:sticky;top:0;z-index:20;height:var(--nav);padding:0 var(--gutter);
display:flex;align-items:center;gap:2px;overflow-x:auto;scrollbar-width:none;
background:color-mix(in srgb,var(--surface-2) 94%,transparent);backdrop-filter:blur(12px);
border-bottom:1px solid var(--line)}
.nav::-webkit-scrollbar{display:none}
.nav a{color:var(--muted);font-size:13px;padding:0 11px;height:var(--nav);
display:inline-flex;align-items:center;gap:7px;white-space:nowrap;
border-bottom:2px solid transparent;border-top:2px solid transparent}
.nav a b{font-weight:400;font-size:12px;color:var(--faint)}
.nav a:hover{color:var(--ink);text-decoration:none}
.nav a.on{color:var(--ink);border-bottom-color:var(--accent)}
.nav a.on b{color:var(--accent)}
.nav .sp{flex:1}
.nav .home{display:none;padding:0 14px 0 0;border:0}
.js .nav.scrolled .home{display:inline-flex}
.nav .home .mark{width:16px;height:23px}
.search{position:relative;flex:none;display:none;margin-left:8px}
.js .search{display:block}
.search input{height:30px;width:30px;background:var(--surface);border:1px solid var(--line-2);
border-radius:var(--r);color:var(--ink);padding:0 0 0 30px;font:inherit;font-size:12px;
transition:width .18s ease,padding .18s ease;cursor:pointer}
.search input::placeholder{color:transparent}
.search input:focus,.search input:not(:placeholder-shown){width:250px;padding-right:30px;
cursor:text}
.search input:focus::placeholder{color:var(--faint)}
.search .ic{position:absolute;left:8px;top:8px;color:var(--muted);pointer-events:none}
.search:hover .ic,.search input:focus~.ic{color:var(--ink)}
.search input:focus{outline:none;border-color:var(--accent)}
.search kbd,.search .hits{display:none}
.search input:focus~kbd,.search input:not(:placeholder-shown)~.hits{display:block}
.search kbd{position:absolute;right:8px;top:7px;font-size:10px;color:var(--faint);
border:1px solid var(--line-2);border-radius:var(--r);padding:0 4px;line-height:14px}
.search .hits{position:absolute;right:34px;top:8px;font-size:11px;color:var(--accent)}

/* ── sections ─────────────────────────────────────────────── */
main{padding:0 var(--gutter) 80px;counter-reset:sec}
section{padding:48px 0 12px;border-bottom:1px solid var(--line);counter-increment:sec}
main>section:first-child{padding-top:36px}
section:last-of-type{border-bottom:0}
.h{display:flex;align-items:baseline;gap:14px;margin:0 0 22px;flex-wrap:wrap}
.h h2{margin:0;font-size:19px;font-weight:500;letter-spacing:-.3px;line-height:1.2}
.h h2:before{content:counter(sec,decimal-leading-zero);color:var(--accent);font-size:11px;
letter-spacing:.14em;font-weight:400;margin-right:12px;vertical-align:3px}
.h .n{color:var(--accent);font-size:12px}
.h .n b{font-weight:400;color:var(--muted)}
h3{font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);
font-weight:400;margin:22px 0 8px}
p.note{color:var(--muted);font-size:12px;margin:14px 0 0;max-width:92ch}

/* ── summary cards ────────────────────────────────────────── */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(136px,1fr));gap:1px;
background:var(--line);border:1px solid var(--line);border-radius:var(--r);overflow:hidden}
.card{background:var(--surface);padding:14px 16px 13px;display:flex;flex-direction:column;
gap:3px;color:inherit;position:relative;min-width:0}
a.card:hover{background:var(--surface-2);text-decoration:none}
.card .v{font-size:26px;line-height:1.1;font-weight:500;letter-spacing:-.5px}
.card .v .of{color:var(--faint);font-size:15px;letter-spacing:0}
.card .k{font-size:11.5px;line-height:1.3;letter-spacing:.1em;text-transform:uppercase;
color:var(--muted)}
.card .s{font-size:12px;line-height:1.45;color:var(--muted);overflow-wrap:anywhere;margin-top:4px;
display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.card.alert{box-shadow:inset 0 2px 0 var(--alert)}
.card.alert .v{color:var(--alert)}
.card.accent{box-shadow:inset 0 2px 0 var(--accent)}
.card.accent .v{color:var(--accent)}
.card.origin{box-shadow:inset 0 2px 0 var(--origin)}
.card.origin .v{color:var(--origin)}
.card.metadata{box-shadow:inset 0 2px 0 var(--metadata)}
.card.metadata .v{color:var(--metadata)}
.card.activity{box-shadow:inset 0 2px 0 var(--activity)}
.card.activity .v{color:var(--activity)}
.legend{display:flex;gap:20px;flex-wrap:wrap;font-size:11px;color:var(--muted);margin:16px 0 0}

/* ── tables ───────────────────────────────────────────────── */
.tbl{width:100%;border-collapse:collapse;font-size:12px}
.tbl th{text-align:left;font-weight:400;font-size:10.5px;letter-spacing:.14em;
text-transform:uppercase;color:var(--muted);padding:8px 14px 8px 0;
border-bottom:1px solid var(--line-2);white-space:nowrap;user-select:none}
.tbl th[data-sort]{cursor:pointer}
.tbl th[data-sort]:hover,.tbl th[data-sort]:focus{color:var(--ink);outline:none}
.tbl th .dir{color:var(--accent);margin-left:4px;font-size:10px}
.tbl td{padding:10px 14px 10px 0;border-bottom:1px solid var(--line);vertical-align:top;
color:var(--ink-2)}
.tbl tr:last-child td{border-bottom:0}
.tbl tbody tr:hover td{background:var(--surface)}
.tbl td.num,.tbl th.num{text-align:right;padding-right:14px;white-space:nowrap}
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
.table-block{position:relative}
.table-actions{display:none;position:absolute;top:2px;right:0;z-index:1}
.js .table-actions{display:block}
.js .table-block>.wrap>.tbl th:last-child{padding-right:34px}
.table-copy{width:26px;height:26px;border:0;color:var(--faint);background:var(--bg)}
.table-copy:hover{color:var(--accent)}
.table-copy .ic{width:13px;height:13px}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);
white-space:nowrap}
.table-copy.ok{color:var(--accent)}
.table-copy.no{color:var(--alert)}
.wrap>table.index,.wrap>table.pivots{min-width:860px}
.wrap>table.relationships{min-width:940px}

/* ── timeline ── */
.density{margin:0 0 18px}
.timeline-tools{display:flex;align-items:center;justify-content:space-between;gap:12px;
flex-wrap:wrap;margin:0 0 9px}
.timeline-legend{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.timeline-state{display:flex;align-items:center;gap:10px;color:var(--muted);font-size:11px}
.btn.compact{height:30px;padding:0 10px;font-size:11px}
.density svg{display:block;width:100%;height:86px;background:var(--surface);
border:1px solid var(--line);border-radius:var(--r)}
.density .lane-grid line{stroke:var(--line-2);stroke-width:1;stroke-dasharray:2 5}
.density .time-bin{cursor:pointer;outline:none}
.density .time-bin rect{fill:var(--faint);opacity:.88;transition:opacity .12s,filter .12s}
.density .time-bin rect.origin{fill:var(--origin)}
.density .time-bin rect.metadata{fill:var(--metadata)}
.density .time-bin rect.activity{fill:var(--activity)}
.density .time-bin:hover rect,.density .time-bin:focus rect{opacity:1;filter:brightness(1.25)}
.density .time-bin.on rect{opacity:1;filter:brightness(1.35)}
.density.filtered .time-bin:not(.on){opacity:.28}
.density figcaption{display:flex;justify-content:space-between;font-size:10.5px;
letter-spacing:.06em;color:var(--faint);margin-top:6px}
.tbl.timeline tr.day td{padding:18px 0 6px;color:var(--ink);font-size:11px;letter-spacing:.14em;
text-transform:uppercase;border-bottom:1px solid var(--line-2)}
.tbl.timeline tr.day:first-child td{padding-top:4px}
.tbl.timeline tbody tr.day:hover td{background:none}
.tbl.timeline td:first-child{white-space:nowrap}

/* ── graph ── */
.graph-panel{margin:0 0 22px;border:1px solid var(--line);border-radius:var(--r);
background:var(--surface);overflow:hidden}
.graph-toolbar{display:flex;align-items:end;justify-content:space-between;gap:14px;
padding:12px 14px;border-bottom:1px solid var(--line);background:var(--surface-2)}
.graph-tools{display:flex;align-items:center;gap:6px;flex:none}
.graph-tools .btn{height:34px}
.graph-tools .btn.icon{width:34px}
.graph-tools output{min-width:44px;text-align:center;color:var(--muted);font-size:11px}
.graph-filterbar{display:flex;align-items:center;gap:12px;padding:10px 14px 0;flex-wrap:wrap}
.graph-filterbar .rel-kinds{margin:0}
.graph{margin:0;padding:10px 14px 12px}
.graph-canvas{position:relative}
.graph svg{display:block;width:100%;height:clamp(360px,52vw,620px);background:var(--surface);
border:0;touch-action:none;cursor:grab;user-select:none}
.graph svg.dragging{cursor:grabbing}
.graph .graph-viewport{transform-origin:0 0}
.graph .e{stroke:var(--line-2);stroke-width:1;stroke-opacity:.9;transition:stroke-opacity .15s}
.graph .node circle{fill:var(--faint);stroke:var(--surface);stroke-width:1.5;
transition:opacity .15s}
.graph .t-file circle{fill:var(--accent)}
.graph .t-person circle,.graph .t-org circle,.graph .t-handle circle{fill:var(--activity)}
.graph .t-device circle,.graph .t-camera_model circle{fill:var(--metadata)}
.graph text{font:10px var(--mono);fill:var(--ink-2);text-anchor:middle;pointer-events:none;
paint-order:stroke;stroke:var(--surface);stroke-width:3px;stroke-linejoin:round}
.js .graph .node{cursor:pointer}
.graph .node:focus{outline:none}
.graph .node:hover circle,.graph .node:focus circle,.graph .node.on circle{stroke:var(--ink);
stroke-width:2}
.graph.focused .node:not(.on):not(.near){opacity:.2}
.graph.focused .e{stroke-opacity:.1}
.graph.focused .e.on{stroke:var(--accent);stroke-opacity:1;stroke-width:1.5}
.graph figcaption{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;
font-size:10.5px;letter-spacing:.04em;color:var(--faint);padding-top:8px;
border-top:1px solid var(--line)}
#graph-inspector{color:var(--muted);text-align:right}
.graph-detail{position:absolute;top:12px;right:12px;width:min(340px,calc(100% - 24px));
max-height:calc(100% - 24px);overflow:auto;padding:14px;
background:color-mix(in srgb,var(--surface-2) 94%,transparent);border:1px solid var(--line-2);
border-radius:var(--r);box-shadow:0 12px 32px
rgba(0,0,0,.28);font-size:11px}
.graph-detail-head{display:flex;align-items:center;justify-content:space-between;gap:10px;
color:var(--accent);letter-spacing:.12em;text-transform:uppercase}
.graph-detail-head button{width:24px;height:24px;border:1px solid var(--line-2);
border-radius:var(--r);
color:var(--muted)}
.graph-detail>strong{display:block;margin:10px 0 12px;color:var(--ink);overflow-wrap:anywhere;
font-size:12px;font-weight:500}
.graph-detail dl{display:grid;gap:0;margin:0 0 12px}
.graph-detail dl>div{display:grid;grid-template-columns:92px 1fr;gap:10px;padding:5px 0;
border-top:1px solid var(--line)}
.graph-detail dt{color:var(--faint)}
.graph-detail dd{margin:0;color:var(--ink-2);overflow-wrap:anywhere}
.graph-detail h4{margin:0 0 4px;font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;
font-weight:400;color:var(--faint)}
.graph-detail ul{list-style:none;margin:0 0 12px;padding:0}
.graph-detail li{display:grid;grid-template-columns:minmax(92px,max-content) 1fr;gap:10px;
padding:5px 0;border-top:1px solid var(--line);align-items:start}
.graph-detail li .kind{color:var(--faint);white-space:nowrap}
.graph-detail li .rel-node{min-width:0}
.graph-detail-actions{display:flex;gap:8px;flex-wrap:wrap}
.to-top{position:fixed;right:20px;bottom:20px;z-index:20;width:36px;height:36px;
box-shadow:0 6px 18px rgba(0,0,0,.28)}
.relationship-bar{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin:6px 0 14px}
.relationship-bar h3{margin:0;flex:none}

/* ── relationships ────────────────────────────────────────── */
.rel-controls{display:flex;align-items:end;gap:10px;flex:1;flex-wrap:wrap;margin:0}
.rel-controls label{display:grid;gap:5px;min-width:min(100%,34em);color:var(--muted);
font-size:10.5px;letter-spacing:.12em;text-transform:uppercase}
.rel-controls select,.rel-controls input{width:100%;height:34px;padding:0 10px;
border:1px solid var(--line-2);border-radius:var(--r);background:var(--surface);
color:var(--ink);font:12px/1.4 var(--mono)}
.rel-controls select{padding-right:34px}
.rel-controls select:hover,.rel-controls select:focus,.rel-controls input:focus{
border-color:var(--accent);outline:none}
.rel-find{display:none}
.js .rel-find{display:grid;min-width:min(100%,20em)}
.rel-kinds{display:none;flex-wrap:wrap;gap:6px;margin:0 0 16px}
.js .rel-kinds{display:flex}
.rel-kinds .chip i{width:8px;height:8px;border-radius:50%;background:var(--faint);flex:none}
.rel-kinds .chip i.t-file{background:var(--accent)}
.rel-kinds .chip i.t-person,.rel-kinds .chip i.t-org,.rel-kinds .chip i.t-handle{
background:var(--activity)}
.rel-kinds .chip i.t-device,.rel-kinds .chip i.t-camera_model{background:var(--metadata)}
.rel-node{display:flex;align-items:flex-start;gap:8px;min-width:15em}
.rel-node .pill{margin-top:1px}
.rel-node a,.rel-node .v{overflow-wrap:anywhere}
.rel-focus{display:none;align-items:center;justify-content:center;flex:none;width:22px;
height:22px;border:1px solid var(--line-2);border-radius:var(--r);color:var(--faint);
margin-left:auto}
.rel-focus .ic{width:12px;height:12px}
.js .rel-focus{display:inline-flex}
.rel-focus:hover,.rel-focus:focus{color:var(--accent);border-color:var(--accent);outline:none}
.relationship .arrow{color:var(--faint);text-align:center;padding-top:12px}
.relationship .arrow .ic{display:inline-block}
.relationship .kind{color:var(--ink);min-width:13em}
.relationship .kind .dim{display:block;margin-top:2px}
.relationship details{min-width:18em}
.rel-proof{padding:8px 0;border-bottom:1px solid var(--line)}
.rel-proof:last-child{border-bottom:0}
.rel-proof .fields{grid-template-columns:minmax(80px,max-content) 1fr;margin-top:0}
.relationship-table-tools{display:none;flex:1;align-items:center;gap:10px;flex-wrap:wrap}
.relationship-table-tools .btn{height:34px}
.js .relationship-table-tools{display:flex}
.relationship-table-tools label{display:grid}
.relationship-table-tools label:first-child{flex:1;min-width:min(100%,18em)}
.relationship-table-tools input,.relationship-table-tools select{height:34px;padding:0 10px;
border:1px solid var(--line-2);border-radius:var(--r);background:var(--surface);color:var(--ink);
font:12px/1.4 var(--mono)}
.relationship-table-tools input:focus,.relationship-table-tools select:focus{outline:none;
border-color:var(--accent)}

/* ── marks ────────────────────────────────────────────────── */
.cat{display:inline-flex;align-items:center;gap:6px;font-size:11px;letter-spacing:.06em;
color:var(--ink-2);white-space:nowrap}
.cat:before{content:"";width:8px;height:8px;border-radius:2px;background:var(--c,var(--faint));
flex:none}
.cat.origin{--c:var(--origin)}
.cat.metadata{--c:var(--metadata)}
.cat.activity{--c:var(--activity)}
.cat.none{--c:transparent;color:var(--faint)}
.cat.none:before{box-shadow:inset 0 0 0 1px var(--line-2)}
.dots{display:inline-flex;gap:4px;vertical-align:middle}
.dots i{width:8px;height:8px;border-radius:2px;background:var(--line-2)}
.dots i.o{background:var(--origin)}
.dots i.m{background:var(--metadata)}
.dots i.a{background:var(--activity)}
.flag{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;
border-radius:var(--r);background:var(--alert-soft);color:var(--alert);font-weight:500}
.pill{display:inline-block;font-size:10.5px;letter-spacing:.08em;padding:1px 7px;
border-radius:var(--r);border:1px solid var(--line-2);color:var(--muted);white-space:nowrap}
.pill.match{border-color:transparent;background:var(--surface-2);color:var(--ink-2)}
.pill.strong{border-color:var(--accent);background:none;color:var(--accent)}
.chips{display:none;flex-wrap:wrap;gap:6px;margin:0 0 16px}
.js .chips{display:flex}
.chip{height:26px;padding:0 10px;border:1px solid var(--line-2);border-radius:var(--r);
font-size:11px;color:var(--muted);display:inline-flex;align-items:center;gap:6px}
.chip b{font-weight:400;color:var(--faint)}
.chip:hover{color:var(--ink);border-color:var(--ink-2)}
.chip.on{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.chip.on b{color:var(--accent-ink);opacity:.7}
.copy{display:none;color:var(--faint);margin-left:6px;vertical-align:-3px;opacity:0}
.js .copy{display:inline-flex}
.copy .ic{width:13px;height:13px}
.copy .ic.ok,.copy .ic.no{display:none}
.copy.ok .ic,.copy.no .ic{display:none}
.copy.ok .ic.ok{display:block;color:var(--accent)}
.copy.no .ic.no{display:block;color:var(--alert)}
tr:hover .copy,.rec:hover .copy,dd:hover .copy,.pair:hover .copy,.facts dd:hover .copy{opacity:1}
.copy:hover,.copy:focus{color:var(--accent);opacity:1;outline:none}
.copy.ok,.copy.no{opacity:1}

/* ── findings ─────────────────────────────────────────────── */
.find{display:grid;grid-template-columns:56px 1fr;gap:0 16px;padding:18px 0;
border-bottom:1px solid var(--line)}
.find:last-child{border-bottom:0}
.find .fid{display:inline-flex;align-items:center;height:22px;padding:0 7px;
border:1px solid var(--line-2);border-radius:var(--r);font-size:11px;color:var(--accent)}
.find .fid:hover{text-decoration:none;border-color:var(--accent)}
.find .t{color:var(--ink);font-size:14px;line-height:22px;overflow-wrap:anywhere}
.find .t.warn:before{content:"!";display:inline-flex;align-items:center;justify-content:center;
width:16px;height:16px;border-radius:var(--r);background:var(--alert-soft);color:var(--alert);
margin-right:8px;font-size:11px;vertical-align:1px}
.find .fields{display:flex;flex-wrap:wrap;gap:4px 0;margin:8px 0 0}
.find .fields dt{color:var(--faint);margin-right:8px;white-space:nowrap}
.find .fields dd{margin:0 26px 0 0;color:var(--ink-2)}
.find .files{margin-top:8px;display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12px;
color:var(--muted)}
.find .files a{color:var(--ink-2)}
.find details .files{display:grid;gap:2px;margin-top:8px}
.find .note{color:var(--muted);font-size:12px;margin-top:8px;max-width:92ch}
.find details{margin-top:8px}
.find summary{color:var(--accent);font-size:12px;cursor:pointer}

/* ── pivots ───────────────────────────────────────────────── */
.tabs{display:none;flex-wrap:wrap;gap:2px 0;border-bottom:1px solid var(--line-2);
margin-bottom:16px}
.js .tabs{display:flex}
.tabs button{padding:8px 12px;font-size:12px;color:var(--muted);
border-bottom:2px solid transparent;margin-bottom:-1px;white-space:nowrap}
.tabs button b{font-weight:400;font-size:11px;color:var(--faint);margin-left:6px}
.tabs button:hover{color:var(--ink)}
.tabs button.on{color:var(--ink);border-bottom-color:var(--accent)}
.tabs button.on b{color:var(--accent)}
.js .pane{display:none}
.js .pane.on{display:block}
.pane:before{content:attr(data-label);display:none;font-size:10px;letter-spacing:.14em;
text-transform:uppercase;color:var(--muted);margin:14px 0 6px}
.holder{display:block;white-space:nowrap}

/* ── file detail ──────────────────────────────────────────── */
.file{border:1px solid var(--line);border-radius:var(--r);margin:0 0 12px;background:var(--surface)}
.file>summary{list-style:none;display:grid;grid-template-columns:52px 1fr auto;gap:16px;
align-items:center;padding:13px 18px;cursor:pointer}
.file>summary::-webkit-details-marker{display:none}
.file>summary .id{color:var(--muted)}
.file>summary .name{color:var(--ink);overflow-wrap:anywhere;font-size:13px}
.file>summary .meta{color:var(--faint);font-size:11px;display:flex;gap:12px;align-items:center;
flex-wrap:wrap}
.file>summary .chev{width:14px;height:14px;fill:currentColor;color:var(--faint);
transition:transform .15s}
.file[open]>summary .chev{transform:rotate(90deg)}
.file[open]>summary{border-bottom:1px solid var(--line)}
.file.review{border-left:2px solid var(--alert)}
.rec{display:grid;grid-template-columns:96px 1fr;gap:0 20px;padding:14px 18px;
border-bottom:1px solid var(--line)}
.rec>.fields{grid-column:2}
.rec:last-child{border-bottom:0}
.rec .cat{align-self:start;margin-top:2px}
.rec .src{color:var(--ink);display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.rec .note{color:var(--muted);margin-top:3px}
.rec.silent,.rec.silent .src{color:var(--faint)}
.fields{display:grid;grid-template-columns:minmax(120px,max-content) 1fr;gap:3px 18px;
margin:8px 0 0;font-size:12px}
.fields dt{color:var(--muted);white-space:nowrap}
.fields dd{margin:0;color:var(--ink-2);overflow-wrap:anywhere}
.fields .sub{display:grid;grid-template-columns:minmax(80px,max-content) 1fr;gap:2px 12px;
margin:0;padding:4px 0 4px 10px;border-left:1px solid var(--line)}
.fields ol.numbered{margin:0;padding:0 0 0 1.6em;display:grid;gap:2px}
.extra{display:grid;grid-template-columns:96px 1fr;gap:0 20px;padding:12px 18px;
border-top:1px dashed var(--line);font-size:12px}
.extra .k{color:var(--muted);letter-spacing:.14em;text-transform:uppercase;font-size:10.5px;
padding-top:2px}
.extra ul{margin:0;padding:0;list-style:none;display:grid;gap:4px}
.extra li{color:var(--ink-2);overflow-wrap:anywhere}

/* ── conflicts ────────────────────────────────────────────── */
.conf{display:grid;grid-template-columns:56px 1fr;gap:0 16px;padding:18px 0;
border-bottom:1px solid var(--line)}
.conf:last-child{border-bottom:0}
.conf .cid{display:inline-flex;align-items:center;height:22px;padding:0 7px;
border:1px solid var(--alert);border-radius:var(--r);font-size:11px;color:var(--alert)}
.conf .cid:hover{text-decoration:none;background:var(--alert-soft)}
.conf .t{color:var(--ink);font-size:14px;line-height:22px;overflow-wrap:anywhere}
.conf .field{color:var(--muted);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;
margin:16px 0 0}
.conf .pair{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,18em),1fr));
gap:1px;background:var(--line);border:1px solid var(--line);border-radius:var(--r);
overflow:hidden;margin-top:6px;font-size:12px}
.conf .pair>div{background:var(--surface);padding:10px 14px;min-width:0}
.conf .pair .src{color:var(--muted);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;
margin-bottom:4px}
.conf .pair .v{color:var(--ink);overflow-wrap:anywhere}
.conf .delta{margin-top:8px;color:var(--alert);font-size:12px}
.conf .delta:before{content:"\0394";margin-right:8px;color:var(--faint)}

footer{padding:24px var(--gutter);border-top:1px solid var(--line);display:flex;
justify-content:space-between;flex-wrap:wrap;gap:10px;font-size:11px;letter-spacing:.14em;
text-transform:uppercase;color:var(--faint)}

/* ── narrow ───────────────────────────────────────────────── */
@media (max-width:920px){
.facts{gap:4px 16px}
}
@media (max-width:820px){
.mast-body{gap:0 18px}
.rec{grid-template-columns:1fr}
.rec .cat{margin-bottom:4px}
.rec>.fields{grid-column:1}
.extra{grid-template-columns:1fr}
.search input:focus,.search input:not(:placeholder-shown){width:150px}
.rel-controls{display:grid;grid-template-columns:1fr}
.rel-controls label{min-width:0}
.graph-toolbar{align-items:stretch;flex-direction:column}
.graph-tools{justify-content:flex-end}
.graph svg{height:420px}
.graph-detail{position:absolute;width:calc(100% - 24px)}
.relationship-bar{flex-direction:column;align-items:stretch}
.find,.conf{grid-template-columns:1fr;gap:6px 0}
}
/* ── print: light, flat, everything open ──────────────────── */
@media print{
:root{color-scheme:light;--bg:#fff;--surface:#fff;--surface-2:#f2f3f5;--line:#d5d8dd;
--line-2:#b8bcc3;--ink:#000;--ink-2:#222;--muted:#555;--faint:#777;--accent:#356282;
--origin:#2F8677;--metadata:#5F58AD;--activity:#8E6E2E;--alert:#B5563A}
@page{margin:14mm}
body{font-size:10.5px}
.nav,.mast-actions,.copy,.chips,.tabs,.chev,.btn,.search,.to-top{display:none!important}
.rel-controls,.rel-kinds,.rel-focus{display:none!important}
.graph-toolbar,.timeline-tools,.table-actions,.relationship-table-tools{display:none!important}
.mast{padding-top:0}
summary{cursor:default;list-style:none}
summary::-webkit-details-marker{display:none}
details:not([open])>:not(summary){display:block}
.js .pane,.pane{display:block!important}
.pane:before{display:block}
section{padding:22px 0 6px}
.h{break-after:avoid}
.file,.conf,.find,.card,tr,.rec{break-inside:avoid}
thead{display:table-header-group}
a{color:inherit}
.wrap{overflow:visible}
.graph-panel{border:0;background:transparent}
.graph{padding:0}
.graph svg{height:auto;max-height:none}
.graph.focused .node,.graph.focused .e{opacity:1;stroke-opacity:.9}
.wrap>table.index,.wrap>table.pivots,.wrap>table.relationships{min-width:0}
.tbl th,.tbl td{white-space:normal}
.tbl .path,.tbl .val,.tbl .where,.tbl .found{min-width:0;max-width:none}
.rel-node,.relationship .kind,.relationship details{min-width:0}
.tbl.relationships thead{display:none}
.tbl.relationships tr{display:grid;grid-template-columns:1fr auto 1fr 1fr;gap:4px 10px;
padding:6px 0;border-bottom:1px solid var(--line)}
.tbl.relationships td{display:block;border:0;padding:0}
.tbl.relationships td:last-child{grid-column:1/-1}
.tbl.relationships summary{display:none}
}
""".replace("%LIGHT%", LIGHT)
