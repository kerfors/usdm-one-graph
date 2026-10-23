"""Write m11/protocol.html from m11/protocol.json (built by lift_protocol.py)."""
import json
from collections import Counter
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
for f in fields:
    f["status"] = field_status(f)
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
  .fine { color: var(--muted); font-size: 11.5px; margin: 12px 0 0; }
  .fine a { color: var(--muted); }
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
  .body { font-size: 14px; margin: 6px 0 4px; }
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
  .appendix h3 { font-family: var(--serif); font-weight: 500; font-size: 18px; margin: 24px 0 6px; }
  .appendix li { font-size: 13px; }
  .hide-empty .sec.empty { display: none; }
  .hide-empty nav li.empty { display: none; }
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
  <h1>The CDISC Pilot, laid out as an ICH M11 protocol</h1>
  <p class="lede">Nothing here was typed in or reformatted by hand. The outline is the <b>ICH M11 Template</b> as m11-rdf renders it. Each Template field's value is the result of a <b>query over the Pilot's graph</b>, following the published HL7 and CDISC mapping statements. Where the Pilot's data is odd, the page shows where and why instead of failing. Click a field to see how its value was found.</p>
  <div class="counters">
    <div><b id="c-one"></b><span>Template fields with one value found</span></div>
    <div><b id="c-odd"></b><span>fields where an oddity is visible</span></div>
    <div><b id="c-text"></b><span>M11 sections with text from the Pilot</span></div>
  </div>
  <div class="legend" id="legend"></div>
  <label class="toggle"><input type="checkbox" id="hide"> Only sections with something from the Pilot</label>
  <label class="toggle"><input type="checkbox" id="open"> Show how every field was found</label>
  <nav><ol id="toc"></ol></nav>
  <p class="fine">Draft, not normative. The queries' own reading: a condition clause is run only when it tests a code on the mapped object or on its parent through the target path's last hop; every other clause is shown and not run. Narrative text is placed by the Pilot's section number, the mappings' own rule, and otherwise by its title (this page's join, as on the <a href="index.html">M11 and USDM page</a>). Values are the Pilot's, as published; the Pilot is an example file and not mature. ICH M11 content © ICH (ICH Legal Mentions); ICH M11 Terminology, NCI EVS (CC BY 4.0); USDM and the Pilot from CDISC DDF-RA (CC BY 4.0); mapping statements from HL7 (CC0) and CDISC (CC BY 4.0) as m11-rdf carries them. Not an ICH, CDISC or HL7 artifact.</p>
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

function routeHtml(f) {
  let h = "";
  if (f.element) h += `<div class="route"><div class="row"><span>M11 element</span><span><a href="${esc(f.element.iri)}" target="_blank" rel="noopener"><code>${esc(lastSeg(f.element.iri))}</code></a> ${esc(f.element.label)}</span><span>Template field</span><span>${esc(f.label)} · page ${f.page}${f.optional ? " · optional" : ""}${f.conditional ? " · conditional" : ""}</span></div></div>`;
  else h += `<div class="route">This Template field realises no element in m11-rdf (see m11-rdf's Template report).</div>`;
  for (const r of f.routes) {
    const src = r.sources.map(s => `${s[0]} row ${s[1]}`).join(", ");
    let cls = r.clauses.map(c => {
      const col = c.kind === "run" ? "var(--one)" : c.kind === "section" ? "var(--sect)" : "var(--none)";
      const lab = c.kind === "run" ? (c.on === "parent" ? "run on parent" : "run") : c.kind === "section" ? "section rule" : "not run";
      return `<div class="cl"><b style="background:${col}">${lab}</b>${esc(c.text)}</div>`;
    }).join("");
    h += `<div class="route"><div class="row">
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
doc.insertAdjacentHTML("beforeend", `<div class="cover"><div class="k">ICH M11 Template, filled from the CDISC Pilot (DDF-RA v4.0.0)</div><h2>Clinical Protocol</h2><p>${C.sections} M11 sections in Template order. ${C.placed} receive a section from the Pilot's M11 document, ${C.text} with text. ${C.fields} Template fields, each followed through the published mappings.</p></div>`);
let fid = 0;
D.sections.forEach((s, i) => {
  const d = depth(s.num), hasText = s.pilot.some(p => p.text), empty = !s.pilot.length && !s.fields.some(f => ["one","several","not-checked","filtered-out"].includes(f.status));
  const title = s.heading ? s.heading : (s.num ? s.label.slice(s.num.length + 1) : s.label);
  const navCol = hasText ? "var(--one)" : s.pilot.length ? "var(--muted)" : "transparent";
  toc.insertAdjacentHTML("beforeend", `<li class="d${d}${hasText ? " has-text" : ""}${empty ? " empty" : ""}"><a href="#s${i}"><span class="dot" style="background:${navCol};border:1px solid var(--muted)"></span><span class="num">${esc(s.num)}</span><span>${esc(title)}</span></a></li>`);
  let h = `<section class="sec d${d}${s.optional ? " optional" : ""}${empty ? " empty" : ""}" id="s${i}"><h3><span class="n">${esc(s.num)}</span><span class="t">${esc(title)}</span>${s.optional ? '<span class="flag">optional</span>' : ""}${s.conditional ? '<span class="flag">conditional</span>' : ""}<a class="iri" href="${esc(s.iri)}" target="_blank" rel="noopener">${esc(lastSeg(s.iri))}</a></h3>`;
  for (const n of s.notes) h += `<div class="note red">The Pilot's section ${esc(n.num)} “${esc(n.title)}” has this section's title; its number places it at ${esc(n.at.split(".").length ? D.sections.find(x => x.iri === n.at).num : "")}.</div>`;
  if (!s.pilot.length) h += `<p class="pl">No section of the Pilot's M11 document reaches this M11 section.</p>`;
  for (const p of s.pilot) {
    h += `<p class="pl"><span>Pilot section ${esc(p.num)} “${esc(p.title)}”</span><span class="mono">${esc(pil(p.iri))}${p.item ? " → " + esc(pil(p.item)) : ""}</span><span class="pill" style="background:${p.placed_by === "number" ? "var(--one)" : "var(--several)"}">placed by ${esc(p.placed_by)}</span>${p.status !== "agree" ? `<span>${esc(PS[p.status])}</span>` : ""}${p.text ? "" : "<span>heading only, no text</span>"}</p>`;
    if (p.text) h += `<div class="body">${p.text}</div>`;
  }
  if (s.fields.length) {
    h += `<div class="fields${s.num ? " compact" : ""}">`;
    for (const f of s.fields) {
      const id = "f" + (fid++);
      h += `<div class="f-label${f.optional ? " optional" : ""}" data-f="${id}">${esc(f.label)}</div><div class="f-val ${f.status}" data-f="${id}">${valueHtml(f)}</div><div class="route-panel" id="${id}" hidden>${routeHtml(f)}</div>`;
    }
    h += `</div>`;
  }
  doc.insertAdjacentHTML("beforeend", h + "</section>");
});
if (D.unplaced.length) {
  let h = `<div class="appendix"><h3>Pilot sections that reach no M11 section</h3><ul>`;
  for (const p of D.unplaced) h += `<li><span style="font-family:var(--mono);font-size:12px">${esc(p.num)}</span> “${esc(p.title)}” — ${esc(PS[p.status])}${p.text ? " (has text)" : ""}</li>`;
  doc.insertAdjacentHTML("beforeend", h + "</ul></div>");
}
doc.addEventListener("click", e => {
  const t = e.target.closest("[data-f]");
  if (!t || e.target.closest("a")) return;
  const p = document.getElementById(t.dataset.f);
  p.hidden = !p.hidden;
});
document.getElementById("hide").addEventListener("change", e => document.body.classList.toggle("hide-empty", e.target.checked));
document.getElementById("open").addEventListener("change", e => document.querySelectorAll(".route-panel").forEach(p => p.hidden = !e.target.checked));
</script>
</body>
</html>
"""
html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
(HERE / "protocol.html").write_text(html)
print("written m11/protocol.html", len(html), "bytes")
