"""Write m11/protocol.html from m11/protocol.json (built by lift_protocol.py)."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
data = json.loads((HERE / "protocol.json").read_text())

RANK = ["one", "several", "not-checked", "filtered-out", "none", "section-rule"]


def field_status(f):
    if f["element"] is None:
        return "no-element"
    if not f["routes"]:
        return "unmapped"
    return min((r["status"] for r in f["routes"]), key=RANK.index)


fields = [f for s in data["sections"] for f in s["fields"]]
for i, f in enumerate(fields):
    f["status"] = field_status(f)
    f["fid"] = f"f{i}"
for i, sec in enumerate(data["sections"]):
    sec["sid"] = f"s{i}"


# --- the oddity index: grouped by what the mapping asks and what the study carries -----------------
def ref(f):
    return {"fid": f["fid"], "label": f["label"]}


groups = defaultdict(lambda: {"fields": [], "carries": set()})
odd_codes = defaultdict(lambda: {"fields": [], "decode": set()})
for f in fields:
    for r in f["routes"]:
        st = r["status"]
        for c in r.get("candidates", []):
            for k in c["codes"]:
                for x in k["codes"]:
                    if not re.fullmatch(r"C\d+", x["code"]):
                        g = odd_codes[x["code"]]
                        g["decode"].add(x["decode"])
                        if ref(f) not in g["fields"]:
                            g["fields"].append(ref(f))
        if st not in ("filtered-out", "not-checked", "several"):
            continue
        if st == "filtered-out":
            run = [c["text"] for c in r["clauses"] if c["kind"] == "run"]
            key = (st, r["attr"], " | ".join(run) if run else "last hop " + (r["hop"] or ""))
        elif st == "not-checked":
            key = (st, r["attr"], " | ".join(c["text"] for c in r["clauses"] if c["kind"] == "not-run"))
        else:
            key = (st, r["attr"], r["cond"] or "no condition stated")
        g = groups[key]
        if ref(f) not in g["fields"]:
            g["fields"].append(ref(f))
        for c in r.get("candidates", []):
            for k in c["codes"]:
                for x in k["codes"]:
                    g["carries"].add(f"{x['code']} {x['decode']}")
        g["n_all"] = r.get("n_all")
ORDER = {"filtered-out": 0, "several": 1, "not-checked": 2}
data["oddities"] = {
    "routes": [{"status": k[0], "attr": k[1], "clause": k[2], "fields": g["fields"],
                "carries": sorted(g["carries"]), "n_all": g["n_all"]}
               for k, g in sorted(groups.items(), key=lambda kv: (ORDER[kv[0][0]], kv[0][1], kv[0][2]))],
    "codes": [{**c, "fields": odd_codes[c["code"]]["fields"] if c["code"] in odd_codes else []} for c in data["codes"]],
    "differ": [{"sid": sec["sid"], "num": sec["num"], "n": n} for sec in data["sections"] for n in sec["notes"]],
    "copies": [{"sid": sec["sid"], "num": sec["num"], "p": {k: p[k] for k in ("num", "title", "item")}, "copies": p["copies"]}
               for sec in data["sections"] for p in sec["pilot"] if p["copies"]],
    "shared": [{"sid": sec["sid"], "num": sec["num"], "p": {k: p[k] for k in ("num", "title")}, "shared": p["shared"]}
               for sec in data["sections"] for p in sec["pilot"] if p["shared"]],
}
data["counts"] = {
    "sections": len(data["sections"]),
    "placed": sum(1 for s in data["sections"] if s["pilot"]),
    "text": sum(1 for s in data["sections"] if any(p["text"] for p in s["pilot"])),
    "pilot": sum(len(s["pilot"]) for s in data["sections"]) + len(data["unplaced"]),
    "fields": len(fields),
    "field_status": dict(Counter(f["status"] for f in fields)),
}
print(data["counts"])

html = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pilot Protocol, From the Graph</title>
<meta name="description" content="The CDISC Pilot laid out as an ICH M11 protocol, every value found by a query over published graphs, with the oddities shown where they are">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@500&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
  :root {
    --ground: #0F1729; --panel: rgba(24, 34, 56, 0.97); --panel-edge: #2A3652;
    --text: #E6EAF2; --muted: #8A94AB; --amber: #F2B441;
    --paper: #FBFAF6; --ink: #1D2433; --ink-muted: #677089; --rule: #E2DFD6; --blue: #2F3FB0;
    --one: #2E8A4A; --several: #B07A0E; --unchecked: #B07A0E; --out: #C0392B; --none: #8A94AB; --sect: #6F5BC4;
    --sans: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
    --serif: "IBM Plex Serif", Georgia, serif;
    --mono: "IBM Plex Mono", "SFMono-Regular", Menlo, monospace;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--ground); color: var(--text); font-family: var(--sans); font-size: 14px; line-height: 1.45; }
  .panel { position: fixed; top: 20px; left: 20px; bottom: 20px; width: 340px; overflow-y: auto;
           background: var(--panel); border: 1px solid var(--panel-edge); border-radius: 6px; padding: 18px; }
  h1 { font-family: var(--serif); font-weight: 500; font-size: 22px; line-height: 1.2; margin: 0 0 8px; }
  .lede { color: var(--muted); font-size: 13px; margin: 0 0 10px; }
  .lede b { color: var(--text); font-weight: 500; }
  .counters { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 0 0 12px;
              border-top: 1px solid var(--panel-edge); border-bottom: 1px solid var(--panel-edge); padding: 10px 0; }
  .counters b { display: block; font-family: var(--mono); font-weight: 500; font-size: 18px; }
  .counters span { color: var(--muted); font-size: 11px; line-height: 1.25; display: block; }
  .legend { display: grid; gap: 4px; margin: 0 0 12px; font-size: 12px; color: var(--muted); }
  .legend div { display: flex; gap: 8px; align-items: baseline; }
  .legend .n { margin-left: auto; font-family: var(--mono); color: var(--text); }
  .sw { width: 10px; height: 10px; border-radius: 2px; flex: none; align-self: center; }
  .toggle { display: flex; gap: 8px; align-items: center; font-size: 13px; margin: 0 0 6px; cursor: pointer; }
  nav { margin-top: 10px; border-top: 1px solid var(--panel-edge); padding-top: 10px; }
  nav ol { list-style: none; margin: 0; padding: 0; font-size: 12.5px; }
  nav li a { display: flex; gap: 7px; align-items: baseline; padding: 2px 4px; border-radius: 3px; color: var(--muted); text-decoration: none; }
  nav li a:hover { background: rgba(255,255,255,0.05); }
  nav li.has-text a { color: var(--text); }
  nav li .num { font-family: var(--mono); font-size: 11.5px; min-width: 50px; }
  nav li .dot { width: 7px; height: 7px; border-radius: 50%; flex: none; align-self: center; }
  nav li.d2 a { padding-left: 12px; } nav li.d3 a { padding-left: 20px; } nav li.d4 a { padding-left: 28px; }
  .oddlink { color: inherit; text-decoration: none; display: block; }
  .oddlink b { color: var(--amber); text-decoration: underline; text-underline-offset: 3px; }
  .oddlink:hover span { color: var(--text); }
  .legend-box { margin: 0 0 10px; font-size: 12.5px; color: var(--muted); }
  .legend-box summary { cursor: pointer; margin: 0 0 6px; }
  .colophon { border-top: 1px solid var(--rule); margin: 28px 0 0; padding-top: 10px; font-size: 11.5px; color: var(--ink-muted); }
  .colophon a { color: var(--ink-muted); }
  main { margin-left: 380px; padding: 20px 24px 60px 0; }
  .paper { background: var(--paper); color: var(--ink); border-radius: 6px; padding: 40px 56px; max-width: 1000px; }
  .cover { border-bottom: 2px solid var(--ink); padding-bottom: 14px; margin-bottom: 8px; }
  .cover .k { font-family: var(--mono); font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink-muted); }
  .cover h2 { font-family: var(--serif); font-weight: 500; font-size: 24px; margin: 4px 0 6px; }
  .cover p { margin: 0; color: var(--ink-muted); font-size: 13px; }
  .sec { padding: 18px 0 8px; border-top: 1px solid var(--rule); scroll-margin-top: 16px; }
  .sec h3 { font-family: var(--serif); font-weight: 500; margin: 0 0 6px; display: flex; gap: 12px; align-items: baseline; }
  .sec h3 .n { font-family: var(--mono); font-size: 0.8em; color: var(--ink-muted); min-width: 56px; }
  .sec.d1 h3 { font-size: 20px; text-transform: none; } .sec.d2 h3 { font-size: 17px; } .sec.d3 h3, .sec.d4 h3 { font-size: 15px; }
  .sec h3 a.iri { margin-left: auto; font-family: var(--mono); font-size: 11px; color: var(--ink-muted); text-decoration: none; font-weight: 400; }
  .sec h3 a.iri:hover { text-decoration: underline; }
  .sec.optional h3 .t { color: var(--blue); }
  .flag { font-family: var(--sans); font-size: 10.5px; border: 1px solid currentColor; border-radius: 8px; padding: 0 6px; color: var(--blue); }
  .pl { font-size: 12px; color: var(--ink-muted); margin: 0 0 8px; display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline; }
  .pl .mono { font-family: var(--mono); font-size: 11.5px; }
  .pill { font-size: 11px; padding: 0 7px; border-radius: 8px; color: #fff; white-space: nowrap; }
  .note { font-size: 12.5px; background: #FFF4DC; border-left: 3px solid var(--several); padding: 6px 10px; margin: 0 0 8px; }
  .note.red { background: #FCE9E6; border-left-color: var(--out); }
  .body { font-size: 14px; margin: 6px 0 4px; overflow-x: auto; }
  .body table { border-collapse: collapse; margin: 8px 0; font-size: 13px; }
  .body td, .body th { border: 1px solid var(--rule); padding: 4px 8px; vertical-align: top; text-align: left; }
  .body img { max-width: 100%; height: auto; }
  .body .unres, .val .unres { color: var(--out); font-family: var(--mono); font-size: 12px; }
  .fields { display: grid; grid-template-columns: minmax(180px, 34%) 1fr; margin: 8px 0 10px; font-size: 13.5px; border-top: 1px solid var(--rule); }
  .fields.compact { grid-template-columns: minmax(160px, 30%) 1fr; font-size: 13px; }
  .f-label, .f-val { padding: 6px 8px; border-bottom: 1px solid var(--rule); }
  .f-label { color: var(--ink-muted); cursor: pointer; }
  .f-label.optional { color: var(--blue); }
  .f-label:hover { text-decoration: underline; }
  .f-val { border-left: 4px solid var(--none); cursor: pointer; }
  .f-val .val { color: var(--ink); }
  .f-val .why { font-size: 12px; color: var(--ink-muted); }
  .f-val.one { border-left-color: var(--one); }
  .f-val.several { border-left-color: var(--several); }
  .f-val.not-checked { border-left-color: var(--unchecked); border-left-style: dashed; }
  .f-val.not-checked .val { color: var(--ink-muted); }
  .f-val.filtered-out { border-left-color: var(--out); }
  .f-val.section-rule { border-left-color: var(--sect); }
  .f-val ul { margin: 0; padding-left: 18px; }
  .route-panel { grid-column: 1 / -1; background: #F2F0E8; border-bottom: 1px solid var(--rule); padding: 10px 12px; font-size: 12.5px; }
  .route-panel[hidden] { display: none; }
  .route { margin: 0 0 10px; padding: 0 0 8px; border-bottom: 1px dashed var(--rule); }
  .route:last-child { border-bottom: 0; margin: 0; padding: 0; }
  .route .row { display: grid; grid-template-columns: 110px 1fr; gap: 2px 8px; }
  .route .row > span:nth-child(odd) { color: var(--ink-muted); }
  .route a { color: inherit; }
  .route code, .route pre { font-family: var(--mono); font-size: 11.5px; }
  .route pre { background: #fff; border: 1px solid var(--rule); padding: 6px 8px; margin: 6px 0; white-space: pre-wrap; word-break: break-all; }
  .cl { font-family: var(--mono); font-size: 11.5px; }
  .cl b { font-family: var(--sans); font-weight: 600; font-size: 10.5px; padding: 0 5px; border-radius: 6px; color: #fff; margin-right: 4px; }
  .cands { border-collapse: collapse; width: 100%; margin-top: 6px; font-size: 12px; }
  .cands td, .cands th { border-bottom: 1px solid var(--rule); padding: 3px 6px; text-align: left; vertical-align: top; }
  .cands td.mono { font-family: var(--mono); font-size: 11px; }
  .cands tr.kept td:first-child { color: var(--one); font-weight: 600; }
  .cands tr.dropped td { color: var(--ink-muted); }
  .odd { margin: 14px 0 6px; font-size: 13px; }
  .odd details summary { font-size: 13px; margin-top: 8px; }
  .odd summary { cursor: pointer; font-family: var(--serif); font-size: 17px; font-weight: 500; }
  .odd p { color: var(--ink-muted); margin: 6px 0; }
  .odd h4 { font-family: var(--sans); font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--ink-muted); margin: 12px 0 4px; }
  .odd ul { margin: 0; padding-left: 18px; }
  .odd li { margin: 0 0 6px; }
  .odd code { font-family: var(--mono); font-size: 11.5px; overflow-wrap: anywhere; }
  .odd .carries { color: var(--ink-muted); }
  .odd a { color: var(--blue); }
  .appendix h3 { font-family: var(--serif); font-weight: 500; font-size: 18px; margin: 24px 0 6px; }
  .appendix li { font-size: 13px; }
  .hide-empty .sec.empty { display: none; }
  .hide-empty nav li.empty { display: none; }
  .views { display: flex; border: 1px solid var(--panel-edge); border-radius: 6px; overflow: hidden; margin: 0 0 14px; }
  .views button { flex: 1; background: transparent; color: var(--muted); border: 0; padding: 6px 0; font: 500 13px var(--sans); cursor: pointer; }
  .views button[aria-pressed="true"] { background: var(--amber); color: var(--ground); }
  body:not(.simple) .sv { display: none; }
  .simple .dv, .simple .counters, .simple .legend-box, .simple label.toggle, .simple .pl, .simple .note,
  .simple #oddities, .simple .flag, .simple .sec h3 a.iri, .simple .route-panel, .simple .appendix { display: none; }
  .simple.hide-empty .sec.empty, .simple.hide-empty nav li.empty { display: revert; }
  .simple .sec.optional h3 .t { color: inherit; }
  .simple .f-label, .simple .f-label.optional { color: var(--ink-muted); }
  .simple .f-val { border-left: 0; }
  .simple .f-val .ph { color: var(--ink-muted); opacity: 0.75; }
  .simple .f-label:has(+ .f-val .ph), .simple .f-val:has(.ph) { cursor: default; text-decoration: none; }
  .simple .noel { display: none; }
  .graph-box { margin: 0 0 12px; font-size: 12.5px; color: var(--muted); }
  .graph-box summary { cursor: pointer; color: var(--text); margin: 0 0 6px; }
  .graph-box ol { list-style: none; margin: 0 0 6px; padding: 0; }
  .graph-box li { display: grid; grid-template-columns: 24px 1fr; gap: 0 6px; margin: 0 0 5px; }
  .graph-box li span { display: block; }
  .graph-box a { color: var(--text); }
  .graph-box a.st, .graph-box .mono { font-family: var(--mono); font-size: 11.5px; }
  .graph-box a.st { color: var(--amber); text-decoration: none; }
  .hops { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 0; margin: 0 0 8px; font-size: 12px; }
  .hops .node { background: #fff; border: 1px solid var(--rule); border-radius: 4px; padding: 1px 6px; }
  .hops .end { color: var(--ink-muted); font-style: italic; padding: 0 4px; }
  .hops .hop { display: inline-flex; align-items: center; color: var(--ink-muted); font-size: 11px; padding: 0 4px; }
  .hops .hop::before { content: ""; width: 12px; border-top: 2px solid var(--ink-muted); margin-right: 4px; }
  .hops .hop::after { content: "→"; margin-left: 3px; }
  .hops .hop.str::before { border-top-style: dashed; }
  .hops a.st { font-family: var(--mono); font-size: 10.5px; color: var(--blue); text-decoration: none; border: 1px solid currentColor; border-radius: 6px; padding: 0 4px; margin-right: 4px; }
  @media (max-width: 900px) {
    .panel { position: static; width: auto; margin: 16px; }
    main { margin: 0 16px; padding: 0 0 40px; }
    .paper { padding: 20px 16px; }
    .fields, .fields.compact { grid-template-columns: 1fr; }
    .f-label { border-bottom: 0; padding-bottom: 0; }
  }
</style>
</head>
<body>
<aside class="panel">
  <div class="views" role="group" aria-label="View"><button type="button" data-view="simple">Protocol</button><button type="button" data-view="deep">Deep dive</button></div>
  <h1>The CDISC Pilot, laid out as an ICH M11 protocol</h1>
  <p class="lede sv">The CDISC Pilot read from a <b>knowledge graph</b>: the ICH M11 Template as m11-rdf renders it, the published HL7 and CDISC mappings, USDM v4 and the study, brought together by shared identifiers. A grey — marks an M11 element the graph finds no clear value for. Click a filled field, or switch to <b>Deep dive</b>, to see how it was found and where the Pilot and the mappings do not fit.</p>
  <p class="lede dv">Nothing here was typed in or reformatted by hand. The outline is the <b>ICH M11 Template</b> as m11-rdf renders it. Each Template field's value is the result of a <b>query over the knowledge graph</b>, following the published HL7 and CDISC mapping statements. Where the Pilot's data is odd, the page shows where and why instead of failing. Click a field to see how its value was found.</p>
  <div class="counters">
    <div><b id="c-one"></b><span>Template fields with one value found</span></div>
    <div><a class="oddlink" href="#oddities"><b id="c-odd"></b><span>fields where an oddity is visible — see the list</span></a></div>
    <div><b id="c-text"></b><span>M11 sections with text from the Pilot</span></div>
  </div>
  <details class="graph-box" id="gb"><summary>The knowledge graph behind this page</summary><div id="gb-body"></div></details>
  <details class="legend-box"><summary>Field colours</summary><div class="legend" id="legend"></div></details>
  <label class="toggle"><input type="checkbox" id="hide"> Only sections with something from the Pilot</label>
  <label class="toggle"><input type="checkbox" id="open"> Show how every field was found</label>
  <nav><ol id="toc"></ol></nav>
</aside>
<main><div class="paper" id="doc"></div></main>
<script>
const D = __DATA__;
const ST = {
  "one": ["var(--one)", "one value found"],
  "several": ["var(--several)", "several values, the mapping does not say which"],
  "not-checked": ["var(--unchecked)", "values found, but a condition could not be run"],
  "filtered-out": ["var(--out)", "the mapping's condition finds nothing in the Pilot"],
  "none": ["var(--none)", "the mapped attribute has no value in the Pilot"],
  "section-rule": ["var(--sect)", "the section's text, by the mappings' section rule"],
  "unmapped": ["var(--none)", "no mapping statement for this element"],
  "no-element": ["var(--none)", "Template field without an M11 element"]
};
const PS = {
  "agree": "number and title agree", "differ": "number and title point to different sections",
  "number-only": "only the number matches", "title-only": "placed by title only",
  "title-ambiguous": "title fits two sections", "neither": "neither matches"
};
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const lastSeg = iri => iri.split("/").pop();
const pil = iri => iri.slice(D.base.length);
const depth = num => num ? Math.min(num.split(".").length, 4) : 1;

const C = D.counts, FS = C.field_status;
document.getElementById("c-one").textContent = (FS["one"] || 0) + " / " + C.fields;
document.getElementById("c-odd").textContent = (FS["several"] || 0) + (FS["not-checked"] || 0) + (FS["filtered-out"] || 0);
document.getElementById("c-text").textContent = C.text + " / " + C.sections;
{
  const FILES = [["1", "m11", "ICH M11 Template headings and fields, M11 elements"], ["2", "usdm", "USDM v4 classes and attributes"],
                 ["3", "sssom", "HL7 and CDISC mapping statements"], ["4", "pilot", "the study, read through the usdm-rdf JSON-LD context"]];
  let h = `<p>The same knowledge graph as on the M11 and USDM page: four published files, ${FILES.reduce((n, x) => n + D.triples[x[1]], 0).toLocaleString("en-GB")} triples, brought together by shared identifiers.</p><p>Every hop from a Template field to a value is a link one of these files states, by identifier. The page itself matches text in one place only: placing the Pilot's sections on M11 sections by number and title (6a). Click a field in the Deep dive to see its hops.</p><ol>`;
  for (const [k, key, what] of FILES) {
    const u = D.inputs[key], parts = u.split("/");
    h += `<li><a class="st" href="index.html?step=${k}">${k}</a><span><a href="${esc(u)}" target="_blank" rel="noopener" class="mono">${esc(parts[parts.length - 1])}</a> (${esc(parts[4])} ${esc(parts[5])})<span>${D.triples[key].toLocaleString("en-GB")} triples: ${esc(what)}</span></span></li>`;
  }
  h += `</ol><p>The numbers are the steps on the <a href="index.html?step=1">M11 and USDM page</a>, where the same graph is built up one file at a time.</p>`;
  document.getElementById("gb-body").innerHTML = h;
}
const lg = document.getElementById("legend");
for (const k of Object.keys(ST)) {
  if (!FS[k]) continue;
  lg.insertAdjacentHTML("beforeend", `<div><span class="sw" style="background:${ST[k][0]}"></span><span>${esc(ST[k][1])}</span><span class="n">${FS[k]}</span></div>`);
}

function valueHtml(f) {
  const r = f.routes, st = f.status;
  const kept = [];
  for (const x of r) if (x.candidates) for (const c of x.candidates) if (c.kept && (x.status === st)) kept.push(c.value);
  const uniq = [...new Set(kept)].map(v => v.trim() ? v : '<i class="why">(empty string in the Pilot)</i>');
  if (st === "one" || st === "several" || st === "not-checked") {
    const v = uniq.length === 1 ? `<span class="val">${uniq[0]}</span>` : `<ul>${uniq.map(v => `<li class="val">${v}</li>`).join("")}</ul>`;
    const why = st === "one" ? "" : `<div class="why">${esc(ST[st][1])}</div>`;
    return v + why;
  }
  if (st === "filtered-out") {
    const x = r.find(x => x.status === "filtered-out");
    return `<span class="why">— ${esc(ST[st][1])}: ${x.n_all} candidate${x.n_all === 1 ? "" : "s"}, none kept</span>`;
  }
  return `<span class="why">— ${esc(ST[st][1])}</span>`;
}

// --- the simple view: only values that are one value or several values found; the rest as Template placeholders ---
const plainHeading = t => t.replace(/[{}]/g, "").replace(/\s*<#>/g, "").trim();
function simpleValues(f) {
  if (f.status !== "one" && f.status !== "several") return [];
  const kept = [];
  for (const x of f.routes) if (x.candidates) for (const c of x.candidates) if (c.kept && x.status === f.status && c.value.trim()) kept.push(c.value);
  return [...new Set(kept)];
}
// Protocol view: the M11 element's name on the left (m11-rdf carries no universal Template text, so a
// placeholder alone, e.g. <#/%> or [Yes/No], does not say what it asks); the value on the right, or a muted dash
// where the graph finds no clear value.
function simpleLabel(f) {
  return esc(f.element ? f.element.label : f.label);
}
function simpleValue(f, v = simpleValues(f)) {
  if (!v.length) return `<span class="ph">—</span>`;
  return v.length === 1 ? `<span class="val">${v[0]}</span>` : `<ul>${v.map(x => `<li class="val">${x}</li>`).join("")}</ul>`;
}
// Repeating headings (<#>): the instances are the study objects behind the non-empty values of the field that
// realises the heading's element (m11:headingElement); ordered by identifier (the graph holds no order for them).
// A section with study text is not repeated.
function instances(s) {
  if (!/<#>/.test(s.heading || "") || s.pilot.some(p => p.text)) return [];
  const f = s.fields.find(f => f.element && f.element.iri === s.heading_element);
  if (!f || (f.status !== "one" && f.status !== "several")) return [];
  const objs = [];
  for (const x of f.routes) if (x.candidates && x.status === f.status) for (const c of x.candidates)
    if (c.kept && c.value.trim() && !objs.includes(c.s)) objs.push(c.s);
  return objs.sort((a, b) => a.localeCompare(b, undefined, {numeric: true}));
}
// A field's values within one instance: the instance object itself, or objects reached from it by the last hop.
function instanceValues(f, o) {
  if (f.status !== "one" && f.status !== "several") return [];
  const kept = [];
  for (const x of f.routes) if (x.candidates && x.status === f.status) for (const c of x.candidates)
    if (c.kept && c.value.trim() && (c.s === o || c.via.includes(pil(o)))) kept.push(c.value);
  return [...new Set(kept)];
}

const stepLink = k => `<a class="st" href="index.html?step=${k}" title="step ${k} on the M11 and USDM page">${k}</a>`;
const hop = (k, text, str) => `<span class="hop${str ? " str" : ""}">${stepLink(k)}${text}</span>`;
const node = h => `<span class="node">${h}</span>`;
// The route as hops between identifiers, each hop with the step (M11 and USDM page) whose file states it;
// dashed: the one hop that rests on matching text.
function hopsHtml(f, s, r) {
  let h = node(`Template field “${esc(f.label)}”`);
  if (!f.element) return `<div class="hops">${h}<span class="end">realises no M11 element</span></div>`;
  h += hop("1", "m11:realises") + node(`<code>${esc(lastSeg(f.element.iri))}</code> ${esc(f.element.label)}`);
  if (!r) return `<div class="hops">${h}<span class="end">no mapping statement</span></div>`;
  h += hop("3", "m11:mappedTo · " + r.sources.map(x => `${esc(x[0])} row ${esc(x[1])}`).join(", ")) + node(`${stepLink("2")}<code>usdm:${esc(r.attr)}</code>`);
  if (r.status === "section-rule") {
    h += hop("6a", "section number or title, as text", true);
    h += s.pilot.length ? s.pilot.map(p => node(`Pilot section ${esc(p.num)} “${esc(p.title)}”`)).join("") : `<span class="end">no Pilot section placed here</span>`;
  } else {
    h += hop("4", "the same IRI in the study") + node(r.n_all ? `${r.n_kept} of ${r.n_all} study objects kept` : "no study object has it");
  }
  return `<div class="hops">${h}</div>`;
}

function routeHtml(f, s) {
  let h = "";
  if (f.element) h += `<div class="route"><div class="row"><span>M11 element</span><span><a href="${esc(f.element.iri)}" target="_blank" rel="noopener"><code>${esc(lastSeg(f.element.iri))}</code></a> ${esc(f.element.label)}</span><span>Template field</span><span>${esc(f.label)} · page ${f.page}${f.optional ? " · optional" : ""}${f.conditional ? " · conditional" : ""}</span></div></div>`;
  else h += `<div class="route">This Template field realises no element in m11-rdf (see m11-rdf's Template report).</div>`;
  if (!f.element || !f.routes.length) h += hopsHtml(f, s, null);
  for (const r of f.routes) {
    const src = r.sources.map(s => `${s[0]} row ${s[1]}`).join(", ");
    let cls = r.clauses.map(c => {
      const col = c.kind === "run" ? "var(--one)" : c.kind === "section" ? "var(--sect)" : "var(--none)";
      const lab = c.kind === "run" ? (c.on === "parent" ? "run on parent" : "run") : c.kind === "section" ? "section rule" : "not run";
      return `<div class="cl"><b style="background:${col}">${lab}</b>${esc(c.text)}</div>`;
    }).join("");
    h += `<div class="route">${hopsHtml(f, s, r)}<div class="row">
      <span>Stated by</span><span>${esc(src)}</span>
      <span>USDM attribute</span><span><a href="${esc(D.usdm + r.attr)}" target="_blank" rel="noopener"><code>usdm:${esc(r.attr)}</code></a></span>
      <span>Target path</span><span><code>${esc(r.targets.join(" ; "))}</code></span>
      ${r.hop ? `<span>Last hop</span><span><code>${esc(r.hop)}</code> (run)</span>` : ""}
      <span>Condition</span><span>${cls || "none stated"}</span>
      <span>Result</span><span><span class="pill" style="background:${ST[r.status][0]}">${esc(ST[r.status][1])}</span>${r.n_all !== undefined ? ` ${r.n_kept} of ${r.n_all} candidates kept` : ""}</span></div>`;
    if (r.query) h += `<pre>${esc(r.query)}</pre>`;
    if (r.candidates && r.candidates.length) {
      h += `<table class="cands"><thead><tr><th></th><th>Pilot object</th><th>Value</th><th>Codes the condition tests</th></tr></thead><tbody>`;
      for (const c of r.candidates.slice(0, 12)) {
        const codes = c.codes.map(k => k.codes.map(x => `${esc(x.code)} ${esc(x.decode)}`).join("; ") || "no code").join(" | ");
        h += `<tr class="${c.kept ? "kept" : "dropped"}"><td>${c.kept ? "kept" : "—"}</td><td class="mono">${esc(pil(c.s))}${c.via.length ? "<br>via " + c.via.map(esc).join(", ") : ""}</td><td>${c.kept ? c.value : esc(c.value)}</td><td class="mono">${codes}</td></tr>`;
      }
      if (r.candidates.length > 12) h += `<tr><td></td><td colspan="3">… ${r.candidates.length - 12} more</td></tr>`;
      h += `</tbody></table>`;
    }
    h += `</div>`;
  }
  return h;
}

const doc = document.getElementById("doc"), toc = document.getElementById("toc");
doc.insertAdjacentHTML("beforeend", `<div class="cover"><div class="k">ICH M11 Template, filled from the CDISC Pilot (DDF-RA v4.0.0)</div><h2>Clinical Protocol</h2><p class="dv">${C.sections} M11 sections in Template order. ${C.placed} receive a section from the Pilot's M11 document, ${C.text} with text. ${C.fields} Template fields, each followed through the published mappings.</p><p class="sv">${C.text} of ${C.sections} M11 sections with text from the Pilot; ${D.sections.flatMap(s => s.fields).filter(f => simpleValues(f).length).length} of ${C.fields} Template fields with a value.</p></div>`);
{
  const O = D.oddities;
  const flinks = fs => fs.map(f => `<a href="#L${f.fid}" data-open="${f.fid}">${esc(f.label)}</a>`).join(", ");
  const HEAD = {"filtered-out": "The mapping's condition finds nothing", "several": "Several values, and the mapping does not say which",
                "not-checked": "Values found, but a condition could not be run"};
  let h = `<details class="odd" id="oddities"><summary>Where the Pilot and the mappings do not fit</summary>
    <p>Grouped from the queries below: what a mapping asks for, what the Pilot carries instead, and the fields it affects. Nothing here is written by hand; another study would give its own list.</p>`;
  for (const st of ["filtered-out", "several", "not-checked"]) {
    const rs = O.routes.filter(r => r.status === st);
    if (!rs.length) continue;
    h += `<details${st === "filtered-out" ? " open" : ""}><summary><h4 style="display:inline">${esc(HEAD[st])} (${rs.length})</h4></summary><ul>`;
    for (const r of rs) {
      h += `<li><code>usdm:${esc(r.attr)}</code>, ${st === "not-checked" ? "not run: " : st === "several" ? "condition: " : "asks: "}<code>${esc(r.clause)}</code>`;
      if (r.carries.length && st !== "several") h += `<br><span class="carries">the Pilot carries: ${r.carries.map(esc).join("; ")}</span>`;
      h += `<br>${flinks(r.fields)}</li>`;
    }
    h += `</ul></details>`;
  }
  if (O.codes.length) {
    h += `<h4>Codes the Pilot puts in the CDISC code system that are not of the NCIt form C&lt;digits&gt; (${O.codes.length})</h4><ul>`;
    for (const c of O.codes) h += `<li><code>${esc(c.code)}</code> ${c.decode.map(esc).join("; ")} — ${c.n}× on ${c.attrs.map(a => "<code>usdm:" + esc(a) + "</code>").join(", ")}${c.fields.length ? "<br>" + flinks(c.fields) : ""}</li>`;
    h += `</ul>`;
  }
  if (O.copies.length) {
    h += `<h4>The same text held twice, under different content items (${O.copies.length})</h4><p>Found by comparing the text; ${O.shared.length} sections share a content item by identifier.</p><ul>`;
    for (const x of O.copies) h += `<li><a href="#${x.sid}">${esc(x.num)}</a> ${esc(x.p.title)} (<code>${esc(pil(x.p.item))}</code>) = ${x.copies.map(c => `${esc(c.template)} ${esc(c.num)} ${esc(c.title)} (<code>${esc(pil(c.item))}</code>)`).join("; ")}</li>`;
    h += `</ul>`;
  }
  if (O.differ.length) {
    h += `<h4>Pilot sections whose number and title point to different M11 sections (${O.differ.length})</h4><ul>`;
    for (const x of O.differ) h += `<li>Pilot ${esc(x.n.num)} “${esc(x.n.title)}”: by title <a href="#${x.sid}">${esc(x.num || "this section")}</a></li>`;
    h += `</ul>`;
  }
  if (D.unplaced.length) h += `<h4>Pilot sections that reach no M11 section</h4><p>${D.unplaced.length}, listed at the end.</p>`;
  doc.insertAdjacentHTML("beforeend", h + `</details>`);
}
D.sections.forEach((s, i) => {
  const d = depth(s.num), hasText = s.pilot.some(p => p.text), empty = !s.pilot.length && !s.fields.some(f => ["one","several","not-checked","filtered-out"].includes(f.status));
  const title = s.heading ? s.heading : (s.num ? s.label.slice(s.num.length + 1) : s.label);
  const navCol = hasText ? "var(--one)" : s.pilot.length ? "var(--muted)" : "transparent";
  const inst = instances(s);
  toc.insertAdjacentHTML("beforeend", `<li class="d${d}${hasText ? " has-text" : ""}${empty ? " empty" : ""}${inst.length ? " dv" : ""}"><a href="#s${i}"><span class="dot" style="background:${navCol};border:1px solid var(--muted)"></span><span class="num">${esc(s.num)}</span><span class="dv">${esc(title)}</span><span class="sv">${esc(plainHeading(title))}</span></a></li>`);
  let h = `<section class="sec d${d}${s.optional ? " optional" : ""}${empty ? " empty" : ""}${inst.length ? " dv" : ""}" id="${s.sid}"><h3><span class="n">${esc(s.num)}</span><span class="t dv">${esc(title)}</span><span class="t sv">${esc(plainHeading(title))}</span>${s.optional ? '<span class="flag">optional</span>' : ""}${s.conditional ? '<span class="flag">conditional</span>' : ""}<a class="iri" href="${esc(s.iri)}" target="_blank" rel="noopener">${esc(lastSeg(s.iri))}</a></h3>`;
  for (const n of s.notes) h += `<div class="note red">The Pilot's section ${esc(n.num)} “${esc(n.title)}” has this section's title; its number places it at ${esc(n.at.split(".").length ? D.sections.find(x => x.iri === n.at).num : "")}.</div>`;
  if (!s.pilot.length) h += `<p class="pl">No section of the Pilot's M11 document reaches this M11 section.</p>`;
  for (const p of s.pilot) {
    h += `<p class="pl"><span>Pilot section ${esc(p.num)} “${esc(p.title)}”</span><span class="mono">${esc(pil(p.iri))}${p.item ? " → " + esc(pil(p.item)) : ""}</span><span class="pill" style="background:${p.placed_by === "number" ? "var(--one)" : "var(--several)"}">placed by ${esc(p.placed_by)}</span>${p.status !== "agree" ? `<span>${esc(PS[p.status])}</span>` : ""}${p.text ? "" : "<span>heading only, no text</span>"}</p>`;
    for (const x of p.shared) h += `<div class="note">The same content item is also section ${esc(x.num)} “${esc(x.title)}” of the ${esc(x.template)} document: one text, one identifier.</div>`;
    for (const x of p.copies) h += `<div class="note">Identical text, under a different content item (<span class="mono">${esc(pil(x.item))}</span>), is section ${esc(x.num)} “${esc(x.title)}” of the ${esc(x.template)} document. Found by comparing the text, not by an identifier: the study holds two copies.</div>`;
    if (p.text) h += `<div class="body">${p.text}</div>`;
  }
  if (s.fields.length) {
    h += `<div class="fields${s.num ? " compact" : ""}">`;
    for (const f of s.fields) {
      const id = f.fid;
      h += `<div class="f-label${f.optional ? " optional" : ""}${f.element ? "" : " noel"}" id="L${id}" data-f="${id}"><span class="dv">${esc(f.label)}</span><span class="sv">${simpleLabel(f)}</span></div><div class="f-val ${f.status}${f.element ? "" : " noel"}" data-f="${id}"><div class="dv">${valueHtml(f)}</div><div class="sv">${simpleValue(f)}</div></div><div class="route-panel" id="${id}" hidden>${routeHtml(f, s)}</div>`;
    }
    h += `</div>`;
  }
  doc.insertAdjacentHTML("beforeend", h + "</section>");
  inst.forEach((o, k) => {
    const parts = s.num.split(".");
    parts[parts.length - 1] = String(Number(parts[parts.length - 1]) + k);
    const num = parts.join("."), t = s.heading.replace(/[{}]/g, "").replace("<#>", String(k + 1)).trim();
    toc.insertAdjacentHTML("beforeend", `<li class="d${d} sv"><a href="#${s.sid}i${k + 1}"><span class="dot" style="background:${navCol};border:1px solid var(--muted)"></span><span class="num">${esc(num)}</span><span>${esc(t)}</span></a></li>`);
    let g = `<section class="sec d${d} sv" id="${s.sid}i${k + 1}"><h3><span class="n">${esc(num)}</span><span class="t">${esc(t)}</span></h3><div class="fields compact">`;
    for (const f of s.fields) {
      const v = instanceValues(f, o);
      g += `<div class="f-label${f.element ? "" : " noel"}" data-f="${f.fid}">${simpleLabel(f)}</div><div class="f-val${f.element ? "" : " noel"}" data-f="${f.fid}">${simpleValue(f, v)}</div>`;
    }
    doc.insertAdjacentHTML("beforeend", g + "</div></section>");
  });
});
if (D.unplaced.length) {
  let h = `<div class="appendix"><h3>Pilot sections that reach no M11 section</h3><ul>`;
  for (const p of D.unplaced) h += `<li><span style="font-family:var(--mono);font-size:12px">${esc(p.num)}</span> “${esc(p.title)}” — ${esc(PS[p.status])}${p.text ? " (has text)" : ""}</li>`;
  doc.insertAdjacentHTML("beforeend", h + "</ul></div>");
}
doc.insertAdjacentHTML("beforeend", `<p class="colophon">Draft, not normative. The queries' own reading: a condition clause is run only when it tests a code on the mapped object or on its parent through the target path's last hop; every other clause is shown and not run. Narrative text is placed by the Pilot's section number, the mappings' own rule, and otherwise by its title (this page's join, as on the <a href="index.html">M11 and USDM page</a>). In the Protocol view a heading with &lt;#&gt; is repeated for each study object behind the field for the heading's element, numbered in the order of the study's identifiers (the graph holds no order for them); each repeat keeps the values of that object and of objects reached from it. Values are the Pilot's, as published; the Pilot is an example file and not mature. ICH M11 content © ICH (ICH Legal Mentions); ICH M11 Terminology, NCI EVS (CC BY 4.0); USDM and the Pilot from CDISC DDF-RA (CC BY 4.0); mapping statements from HL7 (CC0) and CDISC (CC BY 4.0) as m11-rdf carries them. Not an ICH, CDISC or HL7 artifact. · <a href="../">first page</a> · <a href="index.html">M11 and USDM</a> · <a href="https://github.com/kerfors/usdm-one-graph" target="_blank" rel="noopener">source</a></p>`);
doc.addEventListener("click", e => {
  const o = e.target.closest("a[data-open]");
  if (o) {
    const p = document.getElementById(o.dataset.open);
    p.hidden = false;
    const sec = p.closest(".sec");
    if (sec) sec.classList.remove("empty");
    return;
  }
  const t = e.target.closest("[data-f]");
  if (!t || e.target.closest("a")) return;
  const p = document.getElementById(t.dataset.f);
  if (document.body.classList.contains("simple")) {
    if ((t.classList.contains("f-label") ? t.nextElementSibling : t).querySelector(".ph")) return;
    p.hidden = false;
    setView("deep");
    document.getElementById("L" + t.dataset.f).scrollIntoView({block: "center"});
    return;
  }
  p.hidden = !p.hidden;
});
function setView(v) {
  document.body.classList.toggle("simple", v === "simple");
  document.getElementById("gb").open = v === "deep";
  document.querySelectorAll(".views button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.view === v)));
  const u = new URL(location.href);
  if (v === "deep") u.searchParams.set("view", "deep"); else u.searchParams.delete("view");
  if (location.protocol !== "about:") history.replaceState(null, "", u);
}
document.querySelector(".views").addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  const top = [...document.querySelectorAll(".sec")].find(s => s.getBoundingClientRect().bottom > 0);
  setView(b.dataset.view);
  if (top) top.scrollIntoView();
});
setView(new URLSearchParams(location.search).get("view") === "deep" ? "deep" : "simple");
document.querySelector(".oddlink").addEventListener("click", () => { document.getElementById("oddities").open = true; });
document.getElementById("hide").addEventListener("change", e => document.body.classList.toggle("hide-empty", e.target.checked));
document.getElementById("open").addEventListener("change", e => document.querySelectorAll(".route-panel").forEach(p => p.hidden = !e.target.checked));
</script>
</body>
</html>
"""
html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
(HERE / "protocol.html").write_text(html)
print("written m11/protocol.html", len(html), "bytes")
