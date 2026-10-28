"""Write m11/index.html ("ICH M11 and USDM, coming together") from m11/graph.json.

The page is a fixed 2D layout in SVG, built up in five steps. Column order, left to right:
ICH M11 (sections and elements in document order), USDM v4
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
    "attrs": {a: {"label": n["label"], "definition": n["definition"], "step": n["step"], "held": n.get("held", {})} for a, n in attrs.items()},
    "bridges": [{"e": l["s"], "a": l["t"], "both": l["kind"] == "map2", "p": l["p"]} for l in bridges],
    "concepts": [{"id": c["id"], "label": c["label"], "agrees": c.get("agrees", False),
                  "ends": [l["s"] for l in concept_links if l["t"] == c["id"]]}
                 for c in nodes.values() if c["kind"] == "concept"],
    "objs": [{"id": n["id"][len(g["base"]):] if n["id"].startswith(g["base"]) else n["id"], "cls": n["cls"],
              "vals": {k: v for k, v in n["vals"].items() if v}} for n in nodes.values() if n.get("vals")],
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
  .counters .zero.text-join b { color: var(--ok); }
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
  #stage { position: fixed; top: 0; bottom: 0; left: 370px; right: 0; transition: opacity 700ms ease; }
  /* step 5: the protocol read out of the same graph opens over the graph, from the right */
  #proto { position: fixed; z-index: 4; top: 20px; bottom: 20px; right: 20px; width: calc((100vw - 370px) * 0.62 - 20px); display: flex; flex-direction: column;
           background: #FAF8F2; border: 1px solid var(--panel-edge); border-radius: 6px; transform: translateX(calc(100% + 40px)); transition: transform 700ms cubic-bezier(.2, .7, .2, 1); }
  #proto.open { transform: none; }
  #proto .bar { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 8px 12px; background: var(--panel); color: var(--text); font-size: 13px; border-radius: 6px 6px 0 0; }
  #proto .bar a { color: var(--amber); }
  #proto .x { background: var(--amber); border: 0; color: #0F1729; border-radius: 4px; font: 600 12px var(--sans); padding: 5px 12px; cursor: pointer; margin-left: 12px; }
  #proto iframe { flex: 1; border: 0; width: 100%; background: #FAF8F2; border-radius: 0 0 6px 6px; }
  body.proto-open #stage { opacity: 0.55; }
  svg { width: 100%; height: 100%; display: block; }
  .step { transition: opacity 600ms ease; }
  svg:not([data-step]) .step, .step.hidden { opacity: 0; pointer-events: none; }
  .colhead { font-family: var(--mono); font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; fill: var(--muted); transition: fill 400ms ease; }
  .colhead.hl, .legend.hl { fill: var(--amber); font-weight: 600; }
  .chap { font-family: var(--sans); font-size: 10.5px; fill: var(--muted); paint-order: stroke; stroke: #0F1729; stroke-width: 3px; }
  .clabel { font-family: var(--mono); font-size: 10px; fill: #CDBDF5; }
  .clabel.dim { fill: #5E6680; transition: fill 600ms ease; }
  svg[data-step="1"] .clabel.dim, svg[data-step="2"] .clabel.dim { fill: #CDBDF5; }
  .count { font-family: var(--mono); font-size: 10px; fill: var(--muted); }
  .sub, .legend, .srcnote { font-family: var(--sans); font-size: 10.5px; fill: var(--muted); }
  .srcnote { fill: var(--amber); }
  .pick { font-family: var(--sans); font-size: 11px; font-weight: 600; paint-order: stroke; stroke: #0F1729; stroke-width: 4px; }
  .bridges, .bars rect, .bars line, .bars text { transition: opacity 600ms ease, fill 600ms ease; }
  svg[data-step="5"] .bridges { opacity: 0.06; }
  .plabel { font-family: var(--sans); font-size: 10px; fill: #B8C3DE; paint-order: stroke; stroke: #0F1729; stroke-width: 3px; transition: opacity 600ms ease; }
  .grow path, .grow line { stroke-dasharray: 1; stroke-dashoffset: 1; }
  .grow rect { opacity: 0; }
  svg[data-step="5"] .grow path { animation: grow 1.4s ease-out 0.3s forwards; }
  svg[data-step="5"] .grow line.late { animation: grow 0.6s ease-out 1.6s forwards; }
  svg[data-step="5"] .grow rect.late { animation: fadein 0.5s ease-out 2.1s forwards; }
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
  <p class="lede">A graph, built up one published file at a time. Where files share identifiers, they join by themselves.</p>
  <div class="counters">
    <div><b id="c-triples">0</b><span>distinct triples in the merged graph</span></div>
    <div><b id="c-bridges">0</b><span>links from shared identifiers</span></div>
    <div class="zero" id="c-join"><b>0</b><span>lines of join code</span></div>
  </div>
  <div class="nav">
    <button class="btn" id="btn-back" type="button">Back</button>
    <button class="btn primary" id="btn-next" type="button">Load the first file</button>
  </div>
  <ol class="steps" id="steps"></ol>
  <div class="spacer"></div>
  <p class="fine">The identifiers are the work, done once and in public: <a href="https://w3id.org/m11-rdf/" target="_blank" rel="noopener">m11-rdf</a>, <a href="https://w3id.org/cdisc/usdm/v4/" target="_blank" rel="noopener">usdm-rdf</a>. The example study is not fully consistent; it is shown as published. Hover anything for its identifier; click to pin its card and open the links on it.</p>
  <p class="fine">Draft, not normative. ICH M11 © ICH (<a href="https://www.ich.org/page/legal-mentions" target="_blank" rel="noopener">Legal Mentions</a>); ICH M11 Terminology, NCI EVS, CC BY 4.0; USDM, mapping and pilot study, CDISC DDF-RA, CC BY 4.0; HL7 mapping CC0. Not an ICH, CDISC or HL7 artifact. · <a href="../">first page</a> · <a href="protocol.html">the Pilot as an M11 protocol</a> · <a href="https://w3id.org/m11-rdf/slides/" target="_blank" rel="noopener">slides</a> · <a href="https://github.com/kerfors/usdm-one-graph" target="_blank" rel="noopener">source</a></p>
</aside>
<div id="stage"><svg id="svg" xmlns="http://www.w3.org/2000/svg"></svg></div>
<div class="tip" id="tip" hidden></div>
<div id="proto" aria-hidden="true"><div class="bar"><span>The same graph, laid out as an ICH M11 protocol</span><span><a href="protocol.html" target="_blank" rel="noopener">open as its own page ↗</a><button type="button" class="x">Close</button></span></div><iframe title="The study as an ICH M11 protocol"></iframe></div>

<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  const D = JSON.parse(document.getElementById('data').textContent);
  const S = D.steps;
  const fmt = n => n.toLocaleString('en-GB');
  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const NS = 'http://www.w3.org/2000/svg';
  const svg = document.getElementById('svg');
  const R5 = {};

  const file = s => '<a class="file" href="' + s.url + '" target="_blank" rel="noopener">' + s.file + '</a>';
  const SAY = [
    ['ICH M11', () => file(S[0]) + '<br>' + fmt(S[0].triples) + ' triples. 160 sections and 270 elements, each with its own identifier.'],
    ['USDM v4', () => file(S[1]) + '<br>A second file, made independently. Nothing links the two yet.'],
    ['HL7 and CDISC mappings', () => file(S[2]) + '<br>A separate mapping set, published next to the M11 identifiers and pointing at them. Each statement names an M11 element and a USDM attribute, so <b>' + S[2].bridges + ' links</b> appear. No matching. <b style="color:var(--both)">' + S[2].both + '</b> are stated by both CDISC and HL7, <b style="color:var(--one)">' + (S[2].bridges - S[2].both) + '</b> by only one of them.'],
    ['The study\'s structured data', () => file(S[3]) + '<br>' + fmt(S[3].nodes) + ' objects find their ' + S[3].classes_used + ' USDM classes by themselves, through the JSON-LD context.'],
    ['M11 elements → the study\'s structured data', () => 'Through the mapping statements alone, from each ICH M11 element to the study\'s structured data. <b style="color:var(--both)">' + R5.data + ' elements</b> reach ' + R5.attrs + ' attributes that objects in the study hold, in ' + R5.classes + ' classes. ' + R5.none + ' reach only attributes no object in the study holds. ' + R5.text + ' go only to NarrativeContentItem.text, the protocol text (grey): specified by the mappings, not read here. <a class="on" href="protocol.html">The same graph, laid out as an ICH M11 protocol →</a>'],
  ];
  const ol = document.getElementById('steps');
  SAY.forEach((s, i) => {
    const li = document.createElement('li');
    li.innerHTML = '<div class="h"><b>' + ['1', '2', '3', '4', '5'][i] + '</b><span>' + s[0] + '</span></div><div class="say">' + s[1]() + '</div>';
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
    ['g1', 'g2', 'g3', 'g4', 'g5'].forEach((k, i) => { layers[k] = el('g', { class: 'step', 'data-step': i + 1 }); });
    const L = layers;
    // column heads: always shown, so the layout is visible from the start; each step highlights its own
    const heads = el('g', { class: 'heads' });
    el('text', { x: xB, y: 40, 'text-anchor': 'middle', class: 'colhead', 'data-hl': '1 5' }, heads).textContent = 'ICH M11';
    [[css('--both'), 'stated by CDISC and HL7'], [css('--one'), 'stated by only one of them']].forEach(([c, t], i) => {
      el('line', { x1: xB + 20, y1: 52 + i * 12, x2: xB + 30, y2: 52 + i * 12, stroke: c, 'stroke-width': 2 }, L.g3);
      el('text', { x: xB + 34, y: 55.5 + i * 12, class: 'legend', 'data-hl': '3' }, L.g3).textContent = t;
    });
    el('text', { x: xC, y: 40, 'text-anchor': 'middle', class: 'colhead', 'data-hl': '2' }, heads).textContent = 'USDM v4';
    el('text', { x: xC, y: 56, 'text-anchor': 'middle', class: 'sub' }, L.g3).textContent = 'dots: attributes M11 elements link to · dim: no link from M11';
    el('text', { x: xD + 60, y: 40, 'text-anchor': 'middle', class: 'colhead', 'data-hl': '4 5' }, heads).textContent = 'the study: structured data';

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
    const barAt = {};
    D.classes.forEach(c => {
      if (!c.study) return;
      const y = cy[c.id], w = Math.max(2, barMax * Math.sqrt(c.study / maxN));
      el('line', { x1: xC + 3, y1: y, x2: xD, y2: y, stroke: css('--study'), 'stroke-opacity': 0.18, 'stroke-width': 1 }, bars);
      barAt[c.id] = { y, w };
      const r = el('rect', { x: xD, y: y - 2.5, width: w, height: 5, rx: 1.5, fill: css('--study') }, bars);
      el('text', { x: xD + w + 5, y: y + 3.5, class: 'count' }, bars).textContent = fmt(c.study);
      hover(r, () => tipFor('the study\'s objects · CDISC_Pilot_Study.json', null, fmt(c.study) + ' × ' + c.label, '<p class="m">each says rdf:type ' + esc(D.usdm + c.label) + '</p>' + objList(c.label)));
    });

    // step 5: from each M11 element, through the mapping statements alone, to the study's structured data.
    // An attribute reaches the study where objects in the study hold it, by subclass too (SyntaxTemplate-text is
    // held by EligibilityCriterionItem, Endpoint, ...). NarrativeContentItem.text is the protocol text: the mappings
    // specify it, the page does not read it.
    const curveTo = (x1, y1, x2, y2, g, stroke, op, w) => el('path', { d: curve(x1, y1, x2, y2), fill: 'none', stroke, 'stroke-opacity': op, 'stroke-width': w, pathLength: 1, 'pointer-events': 'none' }, g);
    const PROTOCOL_TEXT = D.usdm + 'NarrativeContentItem-text';
    const heldIn = a => Object.keys(D.attrs[a].held || {}).filter(c => barAt[c]);
    const toText = D.bridges.filter(b => b.a === PROTOCOL_TEXT);
    const toData = D.bridges.filter(b => b.a !== PROTOCOL_TEXT && heldIn(b.a).length);
    const g5 = el('g', { class: 'grow' }, L.g5);
    toText.forEach(b => curveTo(xB + 9, sy[b.e], ax[b.a] - 3, ay[b.a], g5, '#6B7898', 0.45, 0.9));
    toData.forEach(b => curveTo(xB + 9, sy[b.e], ax[b.a] - 3, ay[b.a], g5, css('--both'), 0.9, 1.5));
    const heldCls = new Set();
    new Set(toData.map(b => b.a)).forEach(a => heldIn(a).forEach(c => {
      heldCls.add(c);
      const p = curveTo(xC + 3, ay[a], xD, barAt[c].y, g5, css('--both'), 0.9, 1.2); p.classList.add('late');
    }));
    heldCls.forEach(c => el('rect', { x: xD, y: barAt[c].y - 2.5, width: barAt[c].w, height: 5, rx: 1.5, fill: css('--both'), class: 'late', 'pointer-events': 'none' }, g5));
    const eData = new Set(toData.map(b => b.e)), eText = new Set(toText.map(b => b.e));
    const eOther = new Set(D.bridges.filter(b => b.a !== PROTOCOL_TEXT).map(b => b.e));
    R5.data = eData.size; R5.attrs = new Set(toData.map(b => b.a)).size; R5.classes = heldCls.size;
    R5.none = [...eOther].filter(e => !eData.has(e)).length;
    R5.text = [...eText].filter(e => !eOther.has(e)).length;
    ol.children[4].querySelector('.say').innerHTML = SAY[4][1]();
    [[css('--both'), '→ an attribute objects in the study hold'], ['#6B7898', '→ NarrativeContentItem.text: protocol text, not read']].forEach(([c, t], i) => {
      el('line', { x1: xA - 30, y1: top + 6 + i * 14, x2: xA - 22, y2: top + 6 + i * 14, stroke: c, 'stroke-width': 2 }, L.g5);
      el('text', { x: xA - 18, y: top + 9.5 + i * 14, class: 'legend' }, L.g5).textContent = t;
    });
    svg.appendChild(L.labels);
    apply();
  }

  // ---- steps ----------------------------------------------------------------------
  let cur = 0;
  const bNext = document.getElementById('btn-next'), bBack = document.getElementById('btn-back');
  function apply() {
    svg.setAttribute('data-step', cur);
    // the column heads (and the step-3 legend) for what this step adds or joins
    svg.querySelectorAll('[data-hl]').forEach(t => t.classList.toggle('hl', t.dataset.hl.split(' ').includes(String(cur))));
    Object.values(layers).forEach(g => g.classList.toggle('hidden', +g.getAttribute('data-step') > cur));
  }
  function go(k) {
    cur = k; unpin(); if (k < SAY.length) openProto(false);
    [...ol.children].forEach((li, i) => { li.className = i + 1 < k ? 'done' : i + 1 === k ? 'now' : ''; });
    let t = 0, b = 0; S.slice(0, k).forEach(s => { if (s.graph_triples !== undefined) t = s.graph_triples; b += s.bridges; });
    document.getElementById('c-triples').textContent = fmt(t);
    document.getElementById('c-bridges').textContent = fmt(b);
    bNext.textContent = k === 0 ? 'Load the first file' : k < SAY.length ? 'Next' : 'Start again';
    bBack.disabled = k === 0;
    apply();
  }
  // the link in step 5 opens the protocol over the graph instead of leaving the page
  const proto = document.getElementById('proto');
  function openProto(on) {
    if (on && !proto.querySelector('iframe').src) proto.querySelector('iframe').src = 'protocol.html?embed';
    proto.classList.toggle('open', on); proto.setAttribute('aria-hidden', String(!on)); document.body.classList.toggle('proto-open', on);
  }
  ol.addEventListener('click', ev => { const a = ev.target.closest('a.on[href="protocol.html"]'); if (a) { ev.preventDefault(); ev.stopPropagation(); openProto(true); } }, true);
  proto.querySelector('.x').addEventListener('click', () => openProto(false));
  document.addEventListener('keydown', ev => { if (ev.key === 'Escape' && proto.classList.contains('open')) openProto(false); });
  bNext.addEventListener('click', () => go(cur === SAY.length ? 0 : cur + 1));
  bBack.addEventListener('click', () => { if (cur > 0) go(cur - 1); });
  window.addEventListener('resize', draw);
  document.fonts.ready.then(draw);
  draw(); go(['1', '2', '3', '4', '5'].indexOf(new URLSearchParams(location.search).get('step')) + 1);
  window.M11Story = { go };
})();
</script>
"""

html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
out = HERE / "index.html"
out.write_text(html)
print("wrote", out, out.stat().st_size, "bytes")
