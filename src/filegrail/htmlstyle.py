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
--accent:#2F8677;--accent-ink:#FFFFFF;--accent-soft:rgba(47,134,119,.12);
--origin:#2F8677;--metadata:#3E6F9E;--activity:#8E6E2E;--alert:#B5563A;
--alert-soft:rgba(181,86,58,.12)"""

STYLE = """
:root{color-scheme:dark;
--bg:#0F1115;--surface:#151920;--surface-2:#1B2027;--line:#262A31;--line-2:#333944;
--ink:#E6E8EB;--ink-2:#C3C8CE;--muted:#9AA1A9;--faint:#6B727B;
--accent:#5FA89A;--accent-ink:#0F1115;--accent-soft:rgba(95,168,154,.14);
--origin:#5FA89A;--metadata:#7FA3C7;--activity:#C9A66B;--alert:#D08770;
--alert-soft:rgba(208,135,112,.14);
--mono:"IBM Plex Mono","JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
--r:6px;--gutter:clamp(20px,4vw,56px)}
[data-theme=light]{%LIGHT%}
@media (prefers-color-scheme:light){:root:not([data-theme=dark]){%LIGHT%}}
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
.rel-controls select,.rel-controls input{width:100%;height:34px;padding:0 10px;
border:1px solid var(--line-2);border-radius:var(--r);background:var(--surface);
color:var(--ink);font:12px/1.4 var(--mono)}
.rel-controls select{padding-right:34px}
.rel-controls select:hover,.rel-controls select:focus,.rel-controls input:focus{
border-color:var(--accent);outline:none}
.rel-find{display:none}
.js .rel-find{display:grid;min-width:min(100%,20em)}
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
.fields .sub{display:grid;grid-template-columns:minmax(80px,max-content) 1fr;gap:2px 12px;
margin:0;padding:4px 0 4px 10px;border-left:1px solid var(--line)}
.fields ol.numbered{margin:0;padding:0 0 0 1.6em;display:grid;gap:2px}
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

.density{margin:0 0 16px}
.density svg{display:block;width:100%;height:32px;background:var(--surface);
border:1px solid var(--line);border-radius:var(--r)}
.density line{stroke:var(--faint);stroke-width:1.5;stroke-opacity:.8}
.density line.origin{stroke:var(--origin)}
.density line.metadata{stroke:var(--metadata)}
.density line.activity{stroke:var(--activity)}
.density figcaption{display:flex;justify-content:space-between;font-size:11px;color:var(--faint);
margin-top:4px}
.tbl.timeline tr.day td{padding:14px 0 6px;color:var(--muted);font-size:10.5px;
letter-spacing:.14em;text-transform:uppercase;border-bottom:1px solid var(--line-2)}

.graph{margin:0 0 18px}
.graph svg{display:block;width:100%;height:auto;max-height:72vh;background:var(--surface);
border:1px solid var(--line);border-radius:var(--r)}
.graph .e{stroke:var(--line-2);stroke-width:1;stroke-opacity:.8}
.graph .node circle{fill:var(--faint);stroke:var(--surface);stroke-width:1.5}
.graph .t-file circle{fill:var(--accent)}
.graph .t-person circle,.graph .t-org circle,.graph .t-handle circle{fill:var(--activity)}
.graph .t-device circle,.graph .t-camera_model circle{fill:var(--metadata)}
.graph text{font:10px var(--mono);fill:var(--ink-2);text-anchor:middle;pointer-events:none;
paint-order:stroke;stroke:var(--surface);stroke-width:3px;stroke-linejoin:round}
.js .graph .node{cursor:pointer}
.graph .node:focus{outline:none}
.graph .node:hover circle,.graph .node:focus circle,.graph .node.on circle{stroke:var(--ink);
stroke-width:2}
.graph.focused .node:not(.on):not(.near){opacity:.22}
.graph.focused .e{stroke-opacity:.12}
.graph.focused .e.on{stroke:var(--accent);stroke-opacity:1;stroke-width:1.5}
.graph figcaption{font-size:11px;color:var(--faint);margin-top:6px}

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
@page{margin:14mm}
body{font-size:10.5px}
.nav,.mast-actions,.copy,.chips,.tabs,.chev,a.card:after,.btn,.search,
.rel-controls,.rel-kinds,.rel-focus{display:none!important}
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
.graph svg{max-height:none}
.graph.focused .node,.graph.focused .e{opacity:1;stroke-opacity:.8}
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
