"""Write m11/index.html ("ICH M11 and USDM, coming together") from m11/graph.json.

The page is a fixed 2D layout in SVG, built up in six steps. Column order, left to right:
the study's protocol sections, ICH M11 (sections and elements in document order), USDM v4
classes (with the attributes the other files point at), the study's objects per class.
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
g = json.loads((HERE / "graph.json").read_text())
nodes = {n["id"]: n for n in g["nodes"]}
links = g["links"]


def numkey(num):
    return [int(p) for p in num.split(".")]


# --- ICH M11 spine: sections in document order, each followed by the elements it specifies ---
sections = [n for n in nodes.values() if n["kind"] == "section"]
title_page = [s for s in sections if s["label"] == "Title Page"]
amendment = [s for s in sections if s["label"] == "Amendment Details"]
numbered = sorted((s for s in sections if s["num"]), key=lambda s: numkey(s["num"]))
if len(title_page) != 1 or len(amendment) != 1 or len(numbered) != len(sections) - 2:
    raise ValueError("unexpected unnumbered sections")
ordered_sections = title_page + numbered + amendment
first_section = {}
for l in links:
    if l["kind"] == "place" and l["s"] not in first_section:
        first_section[l["s"]] = l["t"]
elements_in = defaultdict(list)
for e, s in first_section.items():
    elements_in[s].append(e)
spine = []
chapter = None
for s in ordered_sections:
    ch = s["label"] if not s["num"] else s["num"].split(".")[0]
    top = (not s["num"]) or "." not in s["num"]
    spine.append({"id": s["id"], "t": "s", "ch": ch, "top": top})
    for e in sorted(elements_in[s["id"]], key=lambda e: min(nodes[e]["blocks"])):
        spine.append({"id": e, "t": "e", "ch": ch})
if sum(1 for x in spine if x["t"] == "e") != sum(1 for n in nodes.values() if n["kind"] == "element"):
    raise ValueError("an element has no place on the spine")
chapters = []
for s in ordered_sections:
    if not s["num"] or "." not in s["num"]:
        label = s["label"]
        short = label if not s["num"] else s["num"] + " " + label.split(" ", 1)[1].capitalize()
        chapters.append({"id": s["id"], "label": short})

# --- USDM column: classes, ordered by where their bridges come from ---------------------
pos = {x["id"]: i for i, x in enumerate(spine)}
attrs = {n["id"]: n for n in nodes.values() if n["kind"] == "attr"}
attr_class = {l["s"]: l["t"] for l in links if l["kind"] == "domain"}
bridges = [l for l in links if l["kind"] in ("map1", "map2")]
concept_links = [l for l in links if l["kind"] == "concept"]
pull = defaultdict(list)
for l in bridges:
    pull[attr_class[l["t"]]].append(pos[l["s"]])
for l in concept_links:
    if l["s"] in pos:
        for l2 in concept_links:
            if l2["t"] == l["t"] and l2["s"] not in pos:
                pull[attr_class.get(l2["s"], l2["s"])].append(pos[l["s"]])
study_count = Counter(n["cls"] for n in nodes.values() if n["kind"] in ("inst", "content"))
classes = [n for n in nodes.values() if n["kind"] == "class"]
usdm = g["usdm"]


def class_key(c):
    p = pull.get(c["id"])
    return (0, sum(p) / len(p)) if p else (1, -study_count.get(c["label"], 0), c["label"])


classes.sort(key=class_key)
attrs_of = defaultdict(list)
for a, c in attr_class.items():
    attrs_of[c].append(a)

# --- the study's protocol sections (step 5) ------------------------------------------
contents = sorted((n for n in nodes.values() if n["kind"] == "content"),
                  key=lambda n: [int(p) if p.isdigit() else 0 for p in n["num"].rstrip(".").split(".")])

steps = g["steps"]
data = {
    "m11": g["m11"], "usdm": usdm, "base": g["base"],
    "steps": [{k: v for k, v in s.items()} for s in steps],
    "spine": spine, "chapters": chapters,
    "sections": {s["id"]: {"label": s["label"], "heading": s["heading"], "page": s["page"]} for s in sections},
    "elements": {n["id"]: {"label": n["label"], "definition": n["definition"], "blocks": n["blocks"],
                           "fields": n["fields"], "records": n.get("records", [])}
                 for n in nodes.values() if n["kind"] == "element"},
    "classes": [{"id": c["id"], "label": c["label"], "definition": c["definition"],
                 "attrs": sorted(attrs_of.get(c["id"], [])), "study": study_count.get(c["label"], 0)} for c in classes],
    "attrs": {a: {"label": n["label"], "definition": n["definition"], "step": n["step"]} for a, n in attrs.items()},
    "bridges": [{"e": l["s"], "a": l["t"], "both": l["kind"] == "map2", "p": l["p"]} for l in bridges],
    "concepts": [{"id": c["id"], "label": c["label"], "agrees": c.get("agrees", False),
                  "ends": [l["s"] for l in concept_links if l["t"] == c["id"]]}
                 for c in nodes.values() if c["kind"] == "concept"],
    "objs": [{"id": n["id"][len(g["base"]):] if n["id"].startswith(g["base"]) else n["id"], "cls": n["cls"],
              "vals": {k: v for k, v in n["vals"].items() if v}} for n in nodes.values() if n.get("vals")],
    "contents": [{"id": n["id"], "num": n["num"], "title": n["title"], "status": n["status"], "by_number": n["by_number"],
                  "by_title": n["by_title"]} for n in contents],
}

html = r"""<title>ICH M11 and USDM, Coming Together</title>
<meta name="description" content="Published files about ICH M11 and USDM v4, loaded as they are: where shared identifiers join them by themselves, and where they do not">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@500&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
  :root {
    --ground: #0F1729; --panel: rgba(24, 34, 56, 0.95); --panel-edge: #2A3652;
    --text: #E6EAF2; --muted: #8A94AB; --amber: #F2B441;
    --m11: #F2B441; --usdm: #B58CFF; --both: #4FC3C8; --one: #E07A9A; --study: #8FA0C9;
    --ok: #7ED491; --bad: #FF6B6B;
    --sans: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
    --serif: "IBM Plex Serif", Georgia, serif;
    --mono: "IBM Plex Mono", "SFMono-Regular", Menlo, monospace;
  }
  html, body { height: 100%; }
  body { margin: 0; background: var(--ground); color: var(--text); font-family: var(--sans); font-size: 14px; line-height: 1.45; overflow: hidden; }
  .panel { position: fixed; z-index: 3; top: 20px; left: 20px; bottom: 20px; width: 330px; overflow-y: auto;
           background: var(--panel); border: 1px solid var(--panel-edge); border-radius: 6px; padding: 18px; box-sizing: border-box;
           display: flex; flex-direction: column; }
  h1 { font-family: var(--serif); font-weight: 500; font-size: 22px; line-height: 1.2; margin: 0 0 8px; }
  .lede { color: var(--muted); font-size: 13px; margin: 0 0 14px; }
  .counters { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 0 0 14px;
              border-top: 1px solid var(--panel-edge); border-bottom: 1px solid var(--panel-edge); padding: 10px 0; }
  .counters b { display: block; font-family: var(--mono); font-weight: 500; font-size: 18px; font-variant-numeric: tabular-nums; }
  .counters span { color: var(--muted); font-size: 11px; line-height: 1.25; display: block; }
  .counters .zero b { color: var(--amber); }
  ol.steps { list-style: none; margin: 0 0 14px; padding: 0; display: grid; gap: 4px; }
  ol.steps li { padding: 7px 9px; border-radius: 4px; color: var(--muted); cursor: pointer; border: 1px solid transparent; }
  ol.steps li:hover { border-color: var(--panel-edge); }
  ol.steps li .h { display: flex; gap: 8px; font-weight: 500; }
  ol.steps li .h b { font-family: var(--mono); font-weight: 500; color: var(--amber); }
  ol.steps li .say { display: none; font-size: 13px; color: var(--text); margin: 4px 0 0 18px; }
  ol.steps li.done { color: var(--text); }
  ol.steps li.now { background: rgba(242,180,65,0.12); border-color: rgba(242,180,65,0.4); color: var(--text); }
  ol.steps li.now .say { display: block; }
  .say .file { font-family: var(--mono); font-size: 12px; color: var(--amber); text-decoration: none; }
  .say .file:hover { text-decoration: underline; }
  .say a.on { color: var(--amber); }
  .nav { display: grid; grid-template-columns: 1fr 2fr; gap: 8px; margin: 0 0 14px; }
  .btn { padding: 9px 12px; border-radius: 4px; border: 1px solid var(--panel-edge); background: rgba(255,255,255,0.03);
         color: var(--text); font: inherit; font-weight: 500; cursor: pointer; }
  .btn:hover, .btn:focus-visible { border-color: var(--amber); outline: none; }
  .btn.primary { background: var(--amber); color: #1A1400; border-color: var(--amber); }
  .btn:disabled { opacity: 0.35; cursor: default; }
  .fine { color: var(--muted); font-size: 11.5px; margin: 0 0 6px; }
  .fine a { color: var(--muted); }
  .spacer { flex: 1; }
  #stage { position: fixed; top: 0; bottom: 0; left: 370px; right: 0; }
  svg { width: 100%; height: 100%; display: block; }
  .step { transition: opacity 600ms ease; }
  svg:not([data-step]) .step, .step.hidden { opacity: 0; pointer-events: none; }
  .colhead { font-family: var(--mono); font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; fill: var(--muted); }
  .chap { font-family: var(--sans); font-size: 10.5px; fill: var(--muted); paint-order: stroke; stroke: #0F1729; stroke-width: 3px; }
  .clabel { font-family: var(--mono); font-size: 10px; fill: #CDBDF5; }
  .clabel.dim { fill: #5E6680; transition: fill 600ms ease; }
  svg[data-step="1"] .clabel.dim, svg[data-step="2"] .clabel.dim { fill: #CDBDF5; }
  .count { font-family: var(--mono); font-size: 10px; fill: var(--muted); }
  .sub, .legend, .srcnote { font-family: var(--sans); font-size: 10.5px; fill: var(--muted); }
  .srcnote { fill: var(--amber); }
  .pick { font-family: var(--sans); font-size: 11px; font-weight: 600; paint-order: stroke; stroke: #0F1729; stroke-width: 4px; }
  .bridges, .bars rect, .bars line, .bars text { transition: opacity 600ms ease, fill 600ms ease; }
  svg[data-step="5"] .bridges, svg[data-step="6"] .bridges { opacity: 0.06; }
  svg[data-step="5"] .bars rect:not(.srcbar), svg[data-step="5"] .bars line, svg[data-step="5"] .bars text:not(.srccount),
  svg[data-step="6"] .bars rect:not(.srcbar), svg[data-step="6"] .bars line, svg[data-step="6"] .bars text:not(.srccount) { opacity: 0.25; }
  svg[data-step="5"] .srcbar, svg[data-step="6"] .srcbar { fill: var(--amber); }
  svg[data-step="5"] .srccount, svg[data-step="6"] .srccount { fill: var(--amber); }
  .plabel { font-family: var(--sans); font-size: 10px; fill: #B8C3DE; paint-order: stroke; stroke: #0F1729; stroke-width: 3px; transition: opacity 600ms ease; }
  svg[data-step="5"] .chap { opacity: 0.3; }
  svg[data-step="6"] .plabel { opacity: 0.4; }
  svg[data-step="7"] .srcbar, svg[data-step="7"] .srccount { fill: var(--amber); }
  svg[data-step="7"] .leg7 { opacity: 0; }
  .grow path, .grow line { stroke-dasharray: 1; stroke-dashoffset: 1; }
  .grow rect { opacity: 0; }
  svg[data-step="7"] .grow path { animation: grow 1.4s ease-out 0.3s forwards; }
  svg[data-step="7"] .grow line.late { animation: grow 0.6s ease-out 1.6s forwards; }
  svg[data-step="7"] .grow rect.late { animation: fadein 0.5s ease-out 2.1s forwards; }
  @keyframes grow { to { stroke-dashoffset: 0; } }
  @keyframes fadein { to { opacity: 1; } }
  .pdot { transition: fill 600ms ease, r 600ms ease; }
  .hit { cursor: pointer; }
  .tip { position: fixed; z-index: 5; pointer-events: none; right: 20px; bottom: 20px; width: 380px; max-width: calc(100vw - 40px);
         max-height: calc(100vh - 60px); overflow: hidden; background: rgba(24,34,56,0.96); box-sizing: border-box;
         border: 1px solid var(--panel-edge); border-radius: 6px; padding: 12px 14px; font-size: 12.5px; }
  .tip.up { bottom: auto; top: 20px; }
  .tip .row { font-family: var(--mono); font-size: 11px; margin: 0 0 5px; line-height: 1.45; }
  .tip .row .a { color: var(--both); }
  .tip .row .v { color: #E6EAF2; font-family: var(--sans); font-size: 12px; }
  .tip .sec { font-family: var(--mono); font-size: 10px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); margin: 8px 0 3px; }
  .tip[hidden] { display: none; }
  .tip .k { font-family: var(--mono); font-size: 10px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); margin: 0 0 2px; }
  .tip .iri { font-family: var(--mono); font-size: 11px; color: var(--amber); word-break: break-all; margin: 0 0 4px; }
  .tip p { margin: 0 0 4px; }
  .tip .m { font-family: var(--mono); font-size: 11px; color: var(--muted); }
  .tip.pinned { pointer-events: auto; overflow-y: auto; border-color: var(--amber); }
  .tip a { color: var(--amber); text-decoration: none; }
  .tip a:hover { text-decoration: underline; }
  .tip .pin { font-family: var(--mono); font-size: 10px; color: var(--muted); margin: 8px 0 0; }
  .tip:not(.pinned) .pin { display: none; }
  @media (max-width: 900px) { .panel { bottom: auto; max-height: 50vh; width: calc(100vw - 40px); } #stage { left: 0; top: 50vh; } }
</style>

<aside class="panel">
  <h1>ICH M11 and USDM, Coming Together</h1>
  <p class="lede">A knowledge graph, built up one published file at a time. Where files share identifiers, they join by themselves.</p>
  <div class="counters">
    <div><b id="c-triples">0</b><span>distinct triples in the merged graph</span></div>
    <div><b id="c-bridges">0</b><span>links from shared identifiers</span></div>
    <div class="zero"><b>0</b><span>lines of join code</span></div>
  </div>
  <div class="nav">
    <button class="btn" id="btn-back" type="button">Back</button>
    <button class="btn primary" id="btn-next" type="button">Load the first file</button>
  </div>
  <ol class="steps" id="steps"></ol>
  <div class="spacer"></div>
  <p class="fine">The identifiers are the work, done once and in public: <a href="https://w3id.org/m11-rdf/" target="_blank" rel="noopener">m11-rdf</a>, <a href="https://w3id.org/cdisc/usdm/v4/" target="_blank" rel="noopener">usdm-rdf</a>. The example study is not fully consistent; it is real. Hover anything for its identifier; click to pin its card and open the links on it.</p>
  <p class="fine">Draft, not normative. ICH M11 © ICH (<a href="https://www.ich.org/page/legal-mentions" target="_blank" rel="noopener">Legal Mentions</a>); ICH M11 Terminology, NCI EVS, CC BY 4.0; USDM, mapping and pilot study, CDISC DDF-RA, CC BY 4.0; HL7 mapping CC0. Not an ICH, CDISC or HL7 artifact. · <a href="../">first page</a> · <a href="protocol.html">the Pilot as an M11 protocol</a> · <a href="https://w3id.org/m11-rdf/slides/" target="_blank" rel="noopener">slides</a> · <a href="https://github.com/kerfors/usdm-one-graph" target="_blank" rel="noopener">source</a></p>
</aside>
<div id="stage"><svg id="svg" xmlns="http://www.w3.org/2000/svg"></svg></div>
<div class="tip" id="tip" hidden></div>

<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  const D = JSON.parse(document.getElementById('data').textContent);
  const S = D.steps.slice(0, 4).concat([{ triples: 0, bridges: 0 }], [D.steps[4]], [{ triples: 0, bridges: 0 }]);
  const fmt = n => n.toLocaleString('en-GB');
  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const NS = 'http://www.w3.org/2000/svg';
  const svg = document.getElementById('svg');
  const st7 = S[5].status;
  const R7 = {};

  const file = s => '<a class="file" href="' + s.url + '" target="_blank" rel="noopener">' + s.file + '</a>';
  const SAY = [
    ['ICH M11', () => file(S[0]) + '<br>' + fmt(S[0].triples) + ' triples. 160 sections and 270 elements, each with its own identifier.'],
    ['USDM v4', () => file(S[1]) + '<br>A second file, made independently. Nothing links the two yet.'],
    ['HL7 and CDISC mappings', () => file(S[2]) + '<br>Each statement names an M11 element and a USDM attribute, so <b>' + S[2].bridges + ' links</b> appear. No matching. <b style="color:var(--both)">' + S[2].both + '</b> are stated by both CDISC and HL7, <b style="color:var(--one)">' + (S[2].bridges - S[2].both) + '</b> by only one of them.'],
    ['The study\'s definitions', () => file(S[3]) + '<br>' + fmt(S[3].nodes) + ' objects find their ' + S[3].classes_used + ' USDM classes by themselves, through the JSON-LD context.'],
    ['The study\'s protocol', () => 'The same study file also holds its protocol: ' + S[5].contents + ' sections, part of the highlighted bar. Each has a number and a title, as text. None carries an ICH M11 identifier, so nothing links them to the spine.'],
    ['Protocol sections → ICH M11 sections', () => 'Each of the ' + S[5].contents + ' protocol sections placed on an ICH M11 section. With no identifier, the section number and title are all there is to go on. <b style="color:var(--ok)">' + st7.agree + '</b> land on the same M11 section by both, <b style="color:var(--bad)">' + st7.differ + '</b> on two different ones, ' + (S[5].contents - st7.agree - st7.differ) + ' on one or none (grey). Hover one to see where.'],
    ['Protocol sections → the study\'s definitions', () => 'From the ' + st7.agree + ' placed sections, through their M11 elements, to the study\'s definitions: ' + R7.els + ' elements reach <b style="color:var(--both)">' + R7.attrs + ' specific USDM attributes</b>, and the objects in the study that hold them. ' + R7.gen + ' reach only NarrativeContentItem.text (grey), which does not say what the text is. Hover a section to see the values. With M11 identifiers in the study\'s definitions, these would all be links: a question for USDM 4.1. <a class="on" href="protocol.html">The same graph, laid out as an ICH M11 protocol →</a>']
  ];
  const ol = document.getElementById('steps');
  SAY.forEach((s, i) => {
    const li = document.createElement('li');
    li.innerHTML = '<div class="h"><b>' + ['1', '2', '3', '4', '5', '6a', '6b'][i] + '</b><span>' + s[0] + '</span></div><div class="say">' + s[1]() + '</div>';
    li.addEventListener('click', () => go(i + 1));
    ol.appendChild(li);
  });

  // ---- layout -------------------------------------------------------------------
  const el = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); (parent || svg).appendChild(e); return e; };
  const layers = {};
  const tip = document.getElementById('tip');
  // the detail card sits in the lower right corner; it moves to the upper right when the pointer is under it
  // click pins the card (as on the first page): it stays, and the pointer can reach its links
  let pinned = null;
  const PIN = '<p class="pin">pinned - click it again or the background to release</p>';
  function unpin() { pinned = null; tip.classList.remove('pinned'); tip.hidden = true; }
  function pin(target, ev, html) {
    if (pinned === target) { unpin(); return; }
    pinned = null; showTip(ev, html); tip.innerHTML += PIN; pinned = target; tip.classList.add('pinned');
  }
  svg.addEventListener('click', ev => { if (pinned && !ev.target.closest('.hit')) unpin(); });
  document.addEventListener('keydown', ev => { if (ev.key === 'Escape' && pinned) unpin(); });
  function showTip(ev, html) {
    if (pinned) return;
    tip.innerHTML = html; tip.hidden = false;
    tip.classList.toggle('up', ev.clientX > window.innerWidth - 420 && ev.clientY > window.innerHeight - tip.offsetHeight - 40);
  }
  function hover(target, html, href) {
    target.classList.add('hit');
    target.addEventListener('mousemove', ev => showTip(ev, html()));
    target.addEventListener('mouseleave', () => { if (!pinned) tip.hidden = true; });
    target.addEventListener('click', ev => pin(target, ev, html()));
  }
  const byAttr = {}, byCls = {};
  D.objs.forEach(o => { (byCls[o.cls] = byCls[o.cls] || []).push(o); Object.entries(o.vals).forEach(([k, v]) => (byAttr[k] = byAttr[k] || []).push({ id: o.id, v })); });
  const nameOf = o => { const k = Object.keys(o.vals).find(k => k.endsWith('-name')); return k ? o.vals[k] : o.id; };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  // the values the study holds for one attribute, grouped by the class of the object that holds them:
  // an attribute of an abstract class (SyntaxTemplate-text) is held by several classes, and the mapping does not say which
  const byClass = vs => {
    const g = {}; vs.forEach(x => { const k = x.id.replace(/_\d+$/, ''); (g[k] = g[k] || []).push(x); });
    const ks = Object.keys(g);
    return (ks.length > 1 ? '<br><span class="m">held by ' + ks.map(k => k + ' ×' + g[k].length).join(', ') + '</span>' : '') +
      ks.slice(0, 3).map(k => '<br>' + esc(g[k][0].id) + ': <span class="v">' + esc(g[k][0].v) + '</span>').join('');
  };
  const objList = cls => {
    const os = byCls[cls] || []; if (!os.length) return '';
    return '<p class="sec">in the study</p>' + os.slice(0, 6).map(o => {
      const other = Object.entries(o.vals).find(([k]) => !k.endsWith('-name'));
      return '<p class="row">' + esc(o.id) + ' · <span class="v">' + esc(nameOf(o)) + '</span>' + (other ? '<br><span class="a">' + esc(other[0]) + '</span> <span class="v">' + esc(other[1]) + '</span>' : '') + '</p>';
    }).join('') + (os.length > 6 ? '<p class="m">+ ' + (os.length - 6) + ' more</p>' : '');
  };
  const tipFor = (kind, iri, title, more) => '<p class="k">' + kind + '</p>' + (iri ? '<p class="iri">' + (iri.startsWith('https://w3id.org/') ? '<a href="' + esc(iri) + '" target="_blank" rel="noopener">' + esc(iri) + '</a>' : esc(iri)) + '</p>' : '') + '<p><b>' + esc(title) + '</b></p>' + (more || '');

  function draw() {
    svg.innerHTML = '';
    unpin();
    const W = svg.clientWidth, H = svg.clientHeight;
    const top = 70, bottom = H - 30;
    const xA = 70, xB = W * 0.32, xC = W * 0.64, xD = W * 0.80;
    ['g1', 'g2', 'g3', 'g4', 'g5', 'g6', 'g7'].forEach((k, i) => { layers[k] = el('g', { class: 'step', 'data-step': i + 1 }); });
    const L = layers;
    // column heads
    el('text', { x: xB, y: 40, 'text-anchor': 'middle', class: 'colhead' }, L.g1).textContent = 'ICH M11';
    [[css('--both'), 'stated by CDISC and HL7'], [css('--one'), 'stated by only one of them']].forEach(([c, t], i) => {
      el('line', { x1: xB + 20, y1: 52 + i * 12, x2: xB + 30, y2: 52 + i * 12, stroke: c, 'stroke-width': 2 }, L.g3);
      el('text', { x: xB + 34, y: 55.5 + i * 12, class: 'legend' }, L.g3).textContent = t;
    });
    el('text', { x: xC, y: 40, 'text-anchor': 'middle', class: 'colhead' }, L.g2).textContent = 'USDM v4';
    el('text', { x: xC, y: 56, 'text-anchor': 'middle', class: 'sub' }, L.g3).textContent = 'dots: attributes M11 elements link to · dim: no link from M11';
    el('text', { x: xD + 60, y: 40, 'text-anchor': 'middle', class: 'colhead' }, L.g4).textContent = 'the study\'s definitions';
    el('text', { x: xA - 30, y: 40, class: 'colhead' }, L.g5).textContent = 'the study\'s protocol';

    // ICH M11 spine
    const sy = {}; const n = D.spine.length; const step = (bottom - top) / (n - 1);
    D.spine.forEach((x, i) => { sy[x.id] = top + i * step; });
    el('line', { x1: xB, y1: top, x2: xB, y2: bottom, stroke: css('--m11'), 'stroke-opacity': 0.25, 'stroke-width': 1 }, L.g1);
    D.spine.forEach(x => {
      const y = sy[x.id];
      if (x.t === 's') {
        const s = D.sections[x.id];
        const c = el('circle', { cx: xB, cy: y, r: x.top ? 4 : 2, fill: css('--m11') }, L.g1);
        hover(c, () => tipFor('ICH M11 section · m11-rdf.ttl', x.id, s.label, s.heading ? '<p class="m">Template: ' + esc(s.heading) + (s.page ? ', page ' + s.page : '') + '</p>' : ''), x.id);
      } else {
        const e = D.elements[x.id];
        const c = el('circle', { cx: xB + 7, cy: y, r: 1.6, fill: '#F7D89A' }, L.g1);
        hover(c, () => tipFor('ICH M11 element · m11-rdf.ttl', x.id, e.label,
          (e.fields.length ? '<p class="m">Template: ' + e.fields.map(f => '&lt;' + esc(f.label) + '&gt; p.' + f.page).join('; ') + '</p>' : '') +
          '<p class="m">Technical Specification block ' + e.blocks.join(', ') + '</p>' +
          (e.records.length ? '<p class="m">mapped by ' + e.records.map(r => r.src + ' ' + r.row).join(', ') + '</p>' : '')), x.id);
      }
    });
    // chapter labels go on a top layer (drawn last) so later lines never cover them; skip one too close to the last
    L.labels = el('g', { class: 'step', 'data-step': 1 });
    let lastY = -100;
    D.chapters.forEach(ch => {
      const y = sy[ch.id];
      if (y - lastY < 13) return;
      lastY = y;
      el('text', { x: xB - 10, y: y + 3.5, 'text-anchor': 'end', class: 'chap' }, L.labels).textContent = ch.label.length > 34 ? ch.label.slice(0, 33) + '…' : ch.label;
    });

    // USDM classes
    const cy = {}; const nc = D.classes.length; const cstep = (bottom - top) / (nc - 1);
    D.classes.forEach((c, i) => { cy[c.id] = top + i * cstep; });
    const ay = {}, ax = {};
    D.classes.forEach(c => {
      const y = cy[c.id];
      const dot = el('circle', { cx: xC, cy: y, r: 3, fill: css('--usdm') }, L.g2);
      hover(dot, () => tipFor('USDM class · usdm_v4.ttl', c.id, c.label, c.definition ? '<p>' + esc(c.definition) + '</p>' : ''), c.id);
      const t = el('text', { x: xC + 8, y: y + 3.5, class: 'clabel' + (c.attrs.length ? '' : ' dim') }, L.g2);
      t.textContent = c.label;
      c.attrs.forEach((a, j) => {
        ay[a] = y; ax[a] = xC - 9 - j * 7;
        const A = D.attrs[a];
        const dot2 = el('circle', { cx: ax[a], cy: y, r: 2.6, fill: '#D9C6FF' }, L.g3);
        hover(dot2, () => tipFor('USDM attribute · usdm_v4.ttl', a, A.label, A.definition ? '<p>' + esc(A.definition) + '</p>' : ''), a);
      });
    });

    // bridges (step 3), drawn under the dots
    const curve = (x1, y1, x2, y2) => 'M' + x1 + ',' + y1 + ' C' + (x1 + (x2 - x1) * 0.5) + ',' + y1 + ' ' + (x1 + (x2 - x1) * 0.5) + ',' + y2 + ' ' + x2 + ',' + y2;
    const bridgeLayer = el('g', { class: 'bridges' }, L.g3); L.g3.insertBefore(bridgeLayer, L.g3.firstChild);
    D.bridges.forEach(b => {
      const p = el('path', { d: curve(xB + 9, sy[b.e], ax[b.a] - 3, ay[b.a]), fill: 'none',
        stroke: b.both ? css('--both') : css('--one'), 'stroke-opacity': b.both ? 0.35 : 0.8, 'stroke-width': b.both ? 0.8 : 1.2 }, bridgeLayer);
      hover(p, () => tipFor('mapping statement · m11-usdm.sssom.ttl', null, D.elements[b.e].label + ' → ' + D.attrs[b.a].label, '<p class="m">' + esc(b.p) + '</p>'));
    });

    // the study's definitions (step 4): one bar per class, length by object count
    const maxN = Math.max(...D.classes.map(c => c.study));
    const barMax = W - xD - 170;
    const bars = el('g', { class: 'bars' }, L.g4);
    let srcY = null, srcX = null, srcN = 0; const barAt = {};
    D.classes.forEach(c => {
      if (!c.study) return;
      const y = cy[c.id], w = Math.max(2, barMax * Math.sqrt(c.study / maxN));
      const src = c.label === 'NarrativeContent';
      if (src) { srcY = y; srcX = xD + w + 30; srcN = c.study; }
      el('line', { x1: xC + 3, y1: y, x2: xD, y2: y, stroke: css('--study'), 'stroke-opacity': 0.18, 'stroke-width': 1 }, bars);
      barAt[c.id] = { y, w };
      const r = el('rect', { x: xD, y: y - 2.5, width: w, height: 5, rx: 1.5, fill: css('--study'), class: src ? 'srcbar' : '' }, bars);
      el('text', { x: xD + w + 5, y: y + 3.5, class: 'count' + (src ? ' srccount' : '') }, bars).textContent = fmt(c.study);
      hover(r, () => tipFor('the study\'s objects · CDISC_Pilot_Study.json', null, fmt(c.study) + ' × ' + c.label, '<p class="m">each says rdf:type ' + esc(D.usdm + c.label) + '</p>' +
        (src ? '<p class="m">' + D.contents.length + ' of them are the sections of its M11-shaped protocol (step 5)</p>' : '') + objList(c.label)));
    });

    // the gap (step 5): the same study's protocol sections. They carry a number and a title as text, no M11 identifier,
    // so the only way to place them in ICH M11 is to match that text. Lines are dashed: matched, not linked.
    // what an M11 section reaches through the mappings: its elements (and those of its subsections) -> bridges -> attributes -> classes
    const lvl = id => { const m = D.sections[id].label.match(/^[\d.]+/); return m ? m[0].replace(/\.$/, '').split('.').length : 1; };
    const secEls = {};
    D.spine.forEach((x, i) => {
      if (x.t !== 's') return;
      const L0 = lvl(x.id), els = [];
      for (let j = i + 1; j < D.spine.length; j++) {
        const y = D.spine[j];
        if (y.t === 's' && lvl(y.id) <= L0) break;
        if (y.t === 'e') els.push(y.id);
      }
      secEls[x.id] = new Set(els);
    });
    const attrClass = {}; D.classes.forEach(c => c.attrs.forEach(a => { attrClass[a] = c.id; }));
    // NarrativeContentItem.text is the generic text holder: a mapping to it does not say which USDM entity the content is about
    const GENERIC = new Set([D.usdm + 'NarrativeContentItem-text']);
    const reach = sids => {
      const els = new Set(); sids.forEach(sid => (secEls[sid] || []).forEach(e => els.add(e)));
      const all = D.bridges.filter(b => els.has(b.e));
      const br = all.filter(b => !GENERIC.has(b.a)), gen = all.filter(b => GENERIC.has(b.a));
      return { br, gen, classes: [...new Set(br.map(b => attrClass[b.a]).filter(c => c && barAt[c]))] };
    };
    const drawReach = (r, color, op, w, g) => {
      r.gen.forEach(b => el('path', { d: curve(xB + 9, sy[b.e], ax[b.a] - 3, ay[b.a]), fill: 'none', stroke: '#6B7898', 'stroke-opacity': op * 0.5, 'stroke-width': w * 0.7, pathLength: 1 }, g));
      r.br.forEach(b => el('path', { d: curve(xB + 9, sy[b.e], ax[b.a] - 3, ay[b.a]), fill: 'none', stroke: color, 'stroke-opacity': op, 'stroke-width': w, pathLength: 1 }, g));
      r.classes.forEach(cid => {
        el('line', { x1: xC + 3, y1: barAt[cid].y, x2: xD, y2: barAt[cid].y, stroke: color, 'stroke-opacity': op, 'stroke-width': w, pathLength: 1, class: 'late' }, g);
        el('rect', { x: xD, y: barAt[cid].y - 2.5, width: barAt[cid].w, height: 5, rx: 1.5, fill: color, class: 'late', 'pointer-events': 'none' }, g);
      });
    };
    const agreed = reach([...new Set(D.contents.filter(c => c.status === 'agree').map(c => c.by_number))]);
    R7.attrs = new Set(agreed.br.map(b => b.a)).size; R7.classes = agreed.classes.length;
    R7.els = new Set(agreed.br.map(b => b.e)).size; const spec = new Set(agreed.br.map(b => b.e)); R7.gen = new Set(agreed.gen.map(b => b.e).filter(e => !spec.has(e))).size;
    ol.children[6].querySelector('.say').innerHTML = SAY[6][1]();
    drawReach(agreed, css('--both'), 0.9, 1.5, el('g', { class: 'grow' }, L.g7));

    const nC = D.contents.length, ktop = top + 64, kstep = (bottom - ktop) / (nC - 1);
    const COL = { agree: css('--ok'), differ: css('--bad'), 'number-only': '#6B7898', 'title-only': '#6B7898', 'title-ambiguous': '#4A5470', neither: '#4A5470' };
    el('text', { x: xA - 30, y: 56, class: 'sub' }, L.g5).textContent = 'number + title, as text';
    if (srcY !== null) el('text', { x: srcX, y: srcY + 3.5, class: 'srcnote' }, L.g5).textContent = '← ' + nC + ' are its protocol';
    const st = D.steps[4].status;
    [[css('--ok'), 'same section by number and title', st.agree], [css('--bad'), 'number and title: two sections', st.differ],
     ['#6B7898', 'only one, or neither, matches', D.contents.length - st.agree - st.differ]].forEach(([c, t, n], i) => {
      el('circle', { cx: xA - 26, cy: top + 6 + i * 14, r: 3, fill: c, class: 'leg7' }, L.g6);
      el('text', { x: xA - 18, y: top + 9.5 + i * 14, class: 'legend leg7' }, L.g6).textContent = n + '  ' + t;
    });
    [[css('--ok'), st.agree + ' placed on an M11 section (6a)'], [css('--both'), '→ reach a specific USDM attribute'], ['#6B7898', '→ reach only NarrativeContentItem.text']].forEach(([c, t], i) => {
      el('line', { x1: xA - 30, y1: top + 6 + i * 14, x2: xA - 22, y2: top + 6 + i * 14, stroke: c, 'stroke-width': 2, 'stroke-dasharray': i ? '' : '2 2' }, L.g7);
      el('text', { x: xA - 18, y: top + 9.5 + i * 14, class: 'legend' }, L.g7).textContent = t;
    });
    const gapLines = el('g', { class: 'gaplines' }, L.g6);
    const pick = el('g', { class: 'step', 'data-step': 5 });
    L.pick = pick;
    const plabs = [];
    D.contents.forEach((c, i) => {
      const y = ktop + i * kstep;
      const bad = c.status === 'differ';
      const tgt = [];
      if (c.by_number) tgt.push([c.by_number, bad ? css('--bad') : COL[c.status], 'by number']);
      if (c.by_title && c.by_title !== c.by_number) tgt.push([c.by_title, css('--ok'), 'by title']);
      const paths = tgt.map(([sid, color]) => el('path', { d: curve(xA + 4, y, xB - 4, sy[sid]), fill: 'none', stroke: color,
        'stroke-dasharray': '3 3', 'stroke-width': bad ? 1.4 : 0.7, 'stroke-opacity': bad ? 0.95 : 0.22, class: c.status === 'agree' ? 'agree' : '' }, gapLines));
      const dot = el('circle', { cx: xA, cy: y, r: 2.4, fill: css('--study'), class: 'pdot hit' + (c.status === 'agree' ? '' : ' nomatch') }, L.g5);
      const lvl1 = !c.num.replace(/\.$/, '').includes('.');
      if (lvl1) {
        dot.dataset.r0 = 3.6; dot.setAttribute('r', 3.6);
        const t = c.num + '  ' + c.title.replace(/\s+/g, ' ');
        plabs.push([y, t.length > 30 ? t.slice(0, 29) + '…' : t]);
      }
      dot.dataset.c = COL[c.status]; dot.dataset.r = lvl1 ? 3.6 : bad ? 3.4 : 2.4;
      const card = () => {
        let h = tipFor('protocol section · CDISC_Pilot_Study.json', c.id, c.num + '  ' + c.title,
          '<p class="m">a NarrativeContent: its number and title are text; no ICH M11 identifier</p>');
        if (cur < 6) return h;
        h += '<p class="sec">6a · placed on ICH M11 section</p>' + (tgt.length ? tgt.map(([sid, color, how]) => '<p class="row"><span style="color:' + color + '">' + how + '</span> → ' + esc(D.sections[sid].label) + '</p>').join('')
          : '<p class="m">' + (c.status === 'title-ambiguous' ? 'title fits two ICH M11 sections' : 'no ICH M11 section by number or title') + '</p>');
        if (cur < 7 || !tgt.length) return h;
        const r = reach(tgt.map(t => t[0]));
        h += '<p class="sec">6b · reaches in the study\'s definitions</p>';
        if (!r.br.length) h += '<p class="m">no specific USDM attribute</p>';
        r.br.slice(0, 5).forEach(b => {
          const a = b.a.slice(D.usdm.length), vs = byAttr[a] || [];
          h += '<p class="row">' + esc(D.elements[b.e].label) + ' → <span class="a">' + esc(a) + '</span>' +
            (vs.length ? byClass(vs) : '<br><span class="m">no text value in the study</span>') + '</p>';
        });
        if (r.br.length > 5) h += '<p class="m">+ ' + (r.br.length - 5) + ' more mappings</p>';
        const g = new Set(r.gen.map(b => b.e)).size;
        if (g) h += '<p class="m">' + g + ' element' + (g > 1 ? 's' : '') + ' only to NarrativeContentItem.text</p>';
        return h;
      };
      dot.addEventListener('mousemove', ev => showTip(ev, card()));
      dot.addEventListener('click', ev => pin(dot, ev, card()));
      dot.addEventListener('mouseenter', () => {
        el('text', { x: xA + 10, y: y - 6, class: 'pick', fill: '#E6EAF2' }, pick).textContent = c.num + '  ' + c.title;
        if (cur < 6) { el('text', { x: xA + 10, y: y + 9, class: 'pick', fill: '#8A94AB' }, pick).textContent = 'text only: no ICH M11 identifier'; return; }
        if (!tgt.length) el('text', { x: xA + 10, y: y + 9, class: 'pick', fill: '#8A94AB' }, pick).textContent = c.status === 'title-ambiguous' ? 'title fits two ICH M11 sections' : 'no ICH M11 section by number or title';
        if (cur >= 7) tgt.forEach(([sid]) => drawReach(reach([sid]), css('--both'), 0.95, 1.6, pick));
        paths.forEach(p => { p.dataset.w = p.getAttribute('stroke-width'); p.dataset.o = p.getAttribute('stroke-opacity'); p.setAttribute('stroke-width', 2.2); p.setAttribute('stroke-opacity', 1); });
        tgt.forEach(([sid, color, how], j) => {
          const t = el('text', { x: xB + 16, y: sy[sid] + 3.5 + (j && Math.abs(sy[sid] - sy[tgt[0][0]]) < 12 ? 13 : 0), class: 'pick', fill: color }, pick);
          t.textContent = how + ': ' + D.sections[sid].label;
        });
      });
      dot.addEventListener('mouseleave', () => {
        if (!pinned) tip.hidden = true;
        paths.forEach(p => { p.setAttribute('stroke-width', p.dataset.w); p.setAttribute('stroke-opacity', p.dataset.o); });
        pick.innerHTML = '';
      });
    });
    // top-level protocol section labels: keep them 11 px apart, push down, then back up from the bottom
    const ly = plabs.map(l => l[0]);
    for (let i = 1; i < ly.length; i++) ly[i] = Math.max(ly[i], ly[i - 1] + 11);
    ly[ly.length - 1] = Math.min(ly[ly.length - 1], bottom + 4);
    for (let i = ly.length - 2; i >= 0; i--) ly[i] = Math.min(ly[i], ly[i + 1] - 11);
    plabs.forEach(([y0, t], i) => {
      if (Math.abs(ly[i] - y0) > 2) el('line', { x1: xA + 4, y1: y0, x2: xA + 8, y2: ly[i], stroke: '#5E6680', 'stroke-width': 0.8 }, L.g5);
      el('text', { x: xA + 10, y: ly[i] + 3.5, class: 'plabel' }, L.g5).textContent = t;
    });
    svg.appendChild(L.labels);
    svg.appendChild(L.pick);
    apply();
  }

  // ---- steps ----------------------------------------------------------------------
  let cur = 0;
  const bNext = document.getElementById('btn-next'), bBack = document.getElementById('btn-back');
  function apply() {
    svg.setAttribute('data-step', cur);
    Object.values(layers).forEach(g => g.classList.toggle('hidden', +g.getAttribute('data-step') > cur));
    svg.querySelectorAll('.pdot').forEach(d => { d.setAttribute('fill', cur >= 6 ? d.dataset.c : css('--study')); d.setAttribute('r', cur >= 6 ? d.dataset.r : (d.dataset.r0 || 2.4)); });
  }
  function go(k) {
    cur = k; unpin();
    [...ol.children].forEach((li, i) => { li.className = i + 1 < k ? 'done' : i + 1 === k ? 'now' : ''; });
    let t = 0, b = 0; S.slice(0, k).forEach(s => { if (s.graph_triples !== undefined) t = s.graph_triples; b += s.bridges; });
    document.getElementById('c-triples').textContent = fmt(t);
    document.getElementById('c-bridges').textContent = fmt(b);
    bNext.textContent = k === 0 ? 'Load the first file' : k < SAY.length ? 'Next' : 'Start again';
    bBack.disabled = k === 0;
    apply();
  }
  bNext.addEventListener('click', () => go(cur === SAY.length ? 0 : cur + 1));
  bBack.addEventListener('click', () => { if (cur > 0) go(cur - 1); });
  window.addEventListener('resize', draw);
  document.fonts.ready.then(draw);
  draw(); go(['1', '2', '3', '4', '5', '6a', '6b'].indexOf(new URLSearchParams(location.search).get('step')) + 1);
  window.M11Story = { go };
})();
</script>
"""

html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
out = HERE / "index.html"
out.write_text(html)
print("wrote", out, out.stat().st_size, "bytes")
