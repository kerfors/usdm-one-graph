import json
from pathlib import Path

HERE = Path(__file__).parent
data = json.loads((HERE / "graph.json").read_text())

FAMILY = {
    "terminology": ["Code", "AliasCode", "ResponseCode"],
    "narrative": ["NarrativeContent", "NarrativeContentItem", "StudyDefinitionDocument",
                  "StudyDefinitionDocumentVersion", "Abbreviation", "CommentAnnotation", "DocumentContentReference"],
    "biomedical": ["BiomedicalConcept", "BiomedicalConceptProperty", "BiomedicalConceptCategory",
                   "BiomedicalConceptSurrogate"],
    "schedule": ["Activity", "ScheduledActivityInstance", "ScheduledDecisionInstance", "Timing",
                 "Encounter", "StudyEpoch", "ScheduleTimeline", "ScheduleTimelineExit", "Procedure",
                 "TransitionRule", "Condition"],
    "eligibility": ["EligibilityCriterion", "EligibilityCriterionItem", "StudyDesignPopulation",
                    "StudyCohort", "Characteristic", "Range", "Quantity"],
    "design": ["Study", "StudyVersion", "StudyDesign", "InterventionalStudyDesign",
               "ObservationalStudyDesign", "StudyArm", "StudyElement", "StudyCell", "StudyTitle",
               "StudyIdentifier", "StudyRole", "StudyAmendment", "StudyAmendmentReason",
               "StudyChange", "StudyAmendmentImpact", "GeographicScope", "GovernanceDate",
               "SubjectEnrollment", "Objective", "Endpoint", "Estimand", "IntercurrentEvent",
               "AnalysisPopulation", "ParameterMap", "SyntaxTemplateDictionary", "Indication", "Organization", "Address", "Masking",
               "StudyIntervention", "AdministrableProduct", "Administration", "AgentAdministration",
               "MedicalDevice", "Ingredient", "Substance", "Strength", "AdministrationDuration",
               "Duration", "Person", "PersonName", "ReferenceIdentifier", "StudySite",
               "AdministrableProductProperty", "AdministrableProductDefinition",
               "AdministrableProductIdentifier", "ProductOrganizationRole", "StudyProduct",
               "MedicalDeviceIdentifier", "Extension", "ExtensionAttribute"],
}
cls_family = {}
for fam, names in FAMILY.items():
    for n in names:
        cls_family[n] = fam
unassigned = sorted(c for c in data["classes"] if c not in cls_family)
print("classes with no family (fall to 'other'):", unassigned)

for c in data["classes"]:
    data["classes"][c]["family"] = cls_family.get(c, "other")

# what the article numbers are: instance triples, typed nodes, ref links
stats = data["stats"]

html = r"""<title>Pilot Study, One Graph</title>
<meta name="description" content="CDISC's pilot study definition lifted into the USDM v4 model and drawn as one graph">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@500&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
  :root {
    --ground: #0F1729;
    --panel: rgba(24, 34, 56, 0.92);
    --panel-edge: #2A3652;
    --text: #E6EAF2;
    --muted: #8A94AB;
    --amber: #F2B441;
    --teal: #4FC3C8;
    --narr: #8FA0C9;
    --green: #7ED491;
    --rose: #E07A9A;
    --purple: #B58CFF;
    --other: #66738F;
    --sans: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
    --serif: "IBM Plex Serif", Georgia, serif;
    --mono: "IBM Plex Mono", "SFMono-Regular", Menlo, monospace;
  }
  html, body { height: 100%; }
  body { margin: 0; background: var(--ground); color: var(--text); font-family: var(--sans);
         font-size: 14px; line-height: 1.45; overflow: hidden; }
  #graph { position: fixed; inset: 0; }
  #graph canvas { outline: none; }

  .panel { position: fixed; z-index: 3; top: 20px; left: 20px; width: 300px; max-height: calc(100vh - 40px);
           overflow-y: auto; background: var(--panel); border: 1px solid var(--panel-edge);
           border-radius: 6px; padding: 18px 18px 14px; box-sizing: border-box;
           backdrop-filter: blur(6px); }
  .eyebrow { font-family: var(--mono); font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase;
             color: var(--muted); margin: 0 0 6px; }
  h1 { font-family: var(--serif); font-weight: 500; font-size: 22px; line-height: 1.2; margin: 0 0 4px;
       text-wrap: balance; }
  .official { color: var(--muted); font-size: 12px; margin: 0 0 8px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .sub { color: var(--muted); margin: 0 0 14px; font-size: 13px; }
  .ns-label { font-family: var(--mono); font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase;
              color: var(--muted); margin: 0 0 2px; }
  .ns { display: block; font-family: var(--mono); font-size: 13px; color: var(--amber); text-decoration: none;
        margin: 0 0 12px; word-break: break-all; }
  .ns:hover { text-decoration: underline; }
  .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 14px; margin: 0 0 16px; }
  .stat b { display: block; font-family: var(--mono); font-weight: 500; font-size: 20px;
            font-variant-numeric: tabular-nums; line-height: 1.1; }
  .stat span { color: var(--muted); font-size: 12px; }

  .legend { display: grid; gap: 4px; margin: 0 0 14px; }
  .fam { display: flex; align-items: center; gap: 9px; padding: 4px 6px; margin: 0 -6px; border-radius: 4px;
         cursor: pointer; border: 0; background: none; color: var(--text); font: inherit; text-align: left; }
  .fam:hover, .fam:focus-visible { background: rgba(255,255,255,0.06); outline: none; }
  .fam.off { opacity: 0.38; }
  .dot { width: 10px; height: 10px; border-radius: 50%; flex: none; }
  .showing { color: var(--muted); font-size: 11px; margin: 4px 0 0; font-family: var(--mono); }
  .fam .n { margin-left: auto; font-family: var(--mono); font-size: 12px; color: var(--muted);
            font-variant-numeric: tabular-nums; }

  .controls { display: grid; gap: 8px; margin: 0 0 12px; }
  .btn { display: flex; align-items: center; justify-content: space-between; gap: 10px;
         padding: 9px 12px; border-radius: 4px; border: 1px solid var(--panel-edge);
         background: rgba(255,255,255,0.03); color: var(--text); font: inherit; font-weight: 500;
         cursor: pointer; text-align: left; }
  .btn:hover, .btn:focus-visible { border-color: var(--amber); outline: none; }
  .btn.primary { border-color: var(--amber); }
  .btn.on { background: var(--amber); color: #1A1400; border-color: var(--amber); }
  .btn small { font-weight: 400; color: inherit; opacity: 0.75; font-size: 12px; }
  .btn.on small { opacity: 0.8; }
  .hint { color: var(--muted); font-size: 12px; margin: 0; }
  .hint code { font-family: var(--mono); font-size: 11px; }

  .card { position: fixed; z-index: 3; right: 20px; bottom: 20px; width: 360px; max-width: calc(100vw - 40px);
          background: var(--panel); border: 1px solid var(--panel-edge); border-radius: 6px;
          padding: 14px 16px; box-sizing: border-box; backdrop-filter: blur(6px); }
  .card[hidden] { display: none; }
  .card .cls { display: flex; align-items: center; gap: 8px; font-weight: 600; margin: 0 0 2px; }
  .card .pref { color: var(--muted); font-size: 12px; margin: 0 0 8px; }
  .card .def { margin: 0 0 10px; font-size: 13px; }
  .card .node { font-family: var(--mono); font-size: 12px; color: var(--muted); margin: 0 0 8px;
                word-break: break-word; }
  .card .node b { color: var(--text); font-weight: 500; }
  .card a { font-family: var(--mono); font-size: 12px; color: var(--amber); text-decoration: none;
            word-break: break-all; display: block; }
  .card a:hover { text-decoration: underline; }
  .card .iri-label { font-family: var(--mono); font-size: 10px; letter-spacing: 0.08em;
                     text-transform: uppercase; color: var(--muted); margin: 8px 0 2px; }
  .card .iri-label:first-child { margin-top: 0; }
  .card a.lead { font-size: 14px; font-weight: 500; color: var(--amber); margin: 0 0 10px; }
  .card .props { display: grid; gap: 2px; }
  .card .props a { display: flex; justify-content: space-between; gap: 10px; }
  .card .props a span:last-child { color: var(--muted); font-variant-numeric: tabular-nums; flex: none; }
  .card .pin { font-family: var(--mono); font-size: 10px; color: var(--muted); margin: 10px 0 0; }
  .card { max-height: calc(100vh - 60px); overflow-y: auto; }

  .foot { position: fixed; z-index: 3; right: 20px; bottom: 10px; color: var(--muted); font-size: 11px;
          font-family: var(--mono); max-width: 420px; text-align: right; margin: 0; }
  .card { bottom: 40px; }
  .foot a { color: var(--muted); }

  .hublabel { position: fixed; z-index: 2; transform: translate(-50%, -50%); pointer-events: none;
              font-family: var(--mono); font-size: 11px; font-weight: 500; color: var(--amber);
              background: rgba(15,23,41,0.7); padding: 1px 5px; border-radius: 3px; white-space: nowrap; }

  @media (max-width: 720px) {
    .panel { width: calc(100vw - 40px); max-height: 46vh; }
    .card { width: calc(100vw - 40px); }
    .foot { display: none; }
  }
  @media (prefers-reduced-motion: reduce) { .btn { transition: none; } }
  html[data-record] .card { width: 460px; font-size: 16px; }
  html[data-record] .card a.lead { font-size: 18px; }
  html[data-record] .card .def { font-size: 15px; }
  html[data-record] .card a, html[data-record] .card .node { font-size: 14px; }
  html[data-record] .card .iri-label { font-size: 11px; }
  html[data-record] .hublabel { font-size: 14px; }
  html[data-record] .hint, html[data-record] .showing { display: none; }
</style>

<div id="graph"></div>

<aside class="panel">
  <p class="eyebrow">usdm-rdf · CDISC pilot study</p>
  <h1 id="title">Pilot Study, One Graph</h1>
  <p class="official" id="official"></p>
  <p class="ns-label">every class and attribute is a name under</p>
  <a class="ns" href="https://w3id.org/cdisc/usdm/v4/" target="_blank" rel="noopener">https://w3id.org/cdisc/usdm/v4/</a>
  <p class="sub">CDISC_Pilot_Study.json read through the published JSON-LD context. No conversion code - every node is typed with a model IRI that resolves.</p>
  <div class="stats">
    <div class="stat"><b id="s-triples"></b><span>statements</span></div>
    <div class="stat"><b id="s-nodes"></b><span>typed objects</span></div>
    <div class="stat"><b id="s-edges"></b><span>links between them</span></div>
    <div class="stat"><b id="s-classes"></b><span>of 80 classes used</span></div>
  </div>
  <div class="legend" id="legend"></div>
  <div class="controls">
    <button class="btn primary" id="btn-model" type="button" aria-pressed="false">
      <span>Show the model</span><small>class IRIs join the graph</small>
    </button>
    <button class="btn" id="btn-labels" type="button" aria-pressed="false">
      <span>Name the classes</span><small>labels on model hubs</small>
    </button>
    <button class="btn" id="btn-replay" type="button">
      <span>Replay from origin</span><small>all nodes start at one point</small>
    </button>
  </div>
  <p class="hint">Hover a node or a link: its IRI. Click a node: pin the card, light up its neighbours. Drag to orbit, scroll to zoom.</p>
</aside>

<div class="card" id="card" hidden>
  <p class="iri-label" id="c-kind">class IRI - resolves</p>
  <a class="lead" id="c-iri" target="_blank" rel="noopener"></a>
  <p class="cls"><span class="dot" id="c-dot"></span><span id="c-cls"></span></p>
  <p class="pref" id="c-pref"></p>
  <p class="def" id="c-def"></p>
  <p class="iri-label" id="c-ncit-label">skos:exactMatch - NCI Thesaurus</p>
  <a id="c-ncit" target="_blank" rel="noopener"></a>
  <p class="iri-label" id="c-node-label">this node - minted under the base chosen at lift, does not resolve</p>
  <p class="node" id="c-node"></p>
  <p class="iri-label" id="c-props-label">its links use these attribute IRIs - each resolves</p>
  <div class="props" id="c-props"></div>
  <p class="pin" id="c-pin" hidden>pinned - click the node again or the background to release</p>
</div>

<p class="foot">source: DDF-RA v4.0.0 · model + context pinned at usdm-rdf v0.7.0 · <a href="https://w3id.org/cdisc/usdm/v4/" target="_blank" rel="noopener">w3id.org/cdisc/usdm/v4/</a></p>

<script src="https://cdn.jsdelivr.net/npm/3d-force-graph@1.73.4/dist/3d-force-graph.min.js"></script>
<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  const D = JSON.parse(document.getElementById('data').textContent);
  const FAM_COLOR = { terminology: '#4FC3C8', narrative: '#8FA0C9', biomedical: '#7ED491',
                      schedule: '#F2B441', eligibility: '#E07A9A', design: '#B58CFF', other: '#66738F' };
  const FAM_NAME = { terminology: 'Terminology (Code, AliasCode, ResponseCode)',
                     narrative: 'Narrative content', biomedical: 'Biomedical concepts',
                     schedule: 'Schedule of activities', eligibility: 'Eligibility & population',
                     design: 'Study, design, interventions, roles', other: 'Other' };
  const ORDER = ['terminology', 'narrative', 'biomedical', 'schedule', 'eligibility', 'design', 'other'];
  const MODEL_COLOR = '#FFFFFF';

  // ---- stats -----------------------------------------------------------------
  const fmt = n => n.toLocaleString('en-GB');
  document.getElementById('s-triples').textContent = fmt(D.stats.instance_triples);
  document.getElementById('s-nodes').textContent = fmt(D.stats.nodes);
  document.getElementById('s-edges').textContent = fmt(D.stats.edges);
  document.getElementById('s-classes').textContent = D.stats.classes_used;
  if (D.study_title) document.getElementById('official').textContent = D.study_title;

  // ---- legend ----------------------------------------------------------------
  const famCount = {};
  D.nodes.forEach(n => { const f = D.classes[n.cls].family; famCount[f] = (famCount[f] || 0) + 1; });
  const famOn = {};
  const OFF_AT_START = { terminology: true, narrative: true };
  const legend = document.getElementById('legend');
  ORDER.filter(f => famCount[f]).forEach(f => {
    famOn[f] = !OFF_AT_START[f];
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'fam' + (famOn[f] ? '' : ' off'); b.dataset.fam = f;
    b.innerHTML = '<span class="dot" style="background:' + FAM_COLOR[f] + '"></span><span>' +
                  FAM_NAME[f] + '</span><span class="n">' + fmt(famCount[f]) + '</span>';
    b.addEventListener('click', () => { famOn[f] = !famOn[f]; b.classList.toggle('off', !famOn[f]); refresh(); });
    legend.appendChild(b);
  });
  const showing = document.createElement('p');
  showing.className = 'showing'; legend.appendChild(showing);
  function updateShowing(d) {
    const n = d.nodes.filter(x => x.kind === 'inst').length;
    showing.textContent = 'showing ' + fmt(n) + ' of ' + fmt(D.stats.nodes) + ' objects - click a family to show or hide it';
  }

  // ---- graph data ------------------------------------------------------------
  const degree = {};
  D.edges.forEach(e => { degree[e.s] = (degree[e.s] || 0) + 1; degree[e.t] = (degree[e.t] || 0) + 1; });
  const instNodes = D.nodes.map(n => ({ id: n.id, cls: n.cls, label: n.label, kind: 'inst',
                                        fam: D.classes[n.cls].family, deg: degree[n.id] || 0 }));
  const instLinks = D.edges.map(e => ({ source: e.s, target: e.t, p: e.p, kind: 'inst' }));

  const hubNodes = Object.keys(D.classes).map(c => ({ id: 'class:' + c, cls: c, kind: 'hub',
                                                        fam: D.classes[c].family, count: D.census[c] }));
  const hubLinks = [];
  D.nodes.forEach(n => hubLinks.push({ source: n.id, target: 'class:' + n.cls, p: 'a', kind: 'type' }));
  Object.keys(D.classes).forEach(c => (D.classes[c].superclass || []).forEach(sup => {
    if (D.classes[sup]) hubLinks.push({ source: 'class:' + c, target: 'class:' + sup, p: 'subClassOf', kind: 'sub' });
  }));

  let showModel = false, showLabels = false;

  function visible(n) { return n.kind === 'hub' ? showModel && famOn[n.fam] : famOn[n.fam]; }
  function currentData() {
    const nodes = instNodes.filter(visible).concat(showModel ? hubNodes.filter(visible) : []);
    const ids = new Set(nodes.map(n => n.id));
    const links = instLinks.concat(showModel ? hubLinks : [])
      .filter(l => ids.has(typeof l.source === 'object' ? l.source.id : l.source) &&
                   ids.has(typeof l.target === 'object' ? l.target.id : l.target));
    return { nodes, links };
  }

  // ---- graph -----------------------------------------------------------------
  const el = document.getElementById('graph');
  const Graph = ForceGraph3D()(el)
    .backgroundColor('#0F1729')
    .showNavInfo(false)
    .nodeId('id')
    .nodeVal(n => n.kind === 'hub' ? 6 + Math.sqrt(n.count) * 2 : 1 + n.deg * 0.35)
    .nodeColor(n => nodeColor(n))
    .nodeOpacity(0.95)
    .nodeResolution(10)
    .nodeRelSize(2.6)
    .nodeLabel(() => '')
    .linkLabel(l => '<span style="font-family:IBM Plex Mono,monospace;font-size:12px;color:#F2B441">' + linkIri(l) + '</span>')
    .linkColor(l => linkColor(l))
    .linkWidth(l => selected && touches(l, selected) ? 1.6 : l.kind === 'sub' ? 1.2 : 0)
    .linkOpacity(0.35)
    .warmupTicks(0)
    .cooldownTicks(400)
    .d3AlphaDecay(0.012)
    .d3VelocityDecay(0.28)
    .onNodeHover(n => { if (!selected) onHover(n); else el.style.cursor = n ? 'pointer' : null; })
    .onNodeClick(n => { selected = (selected && selected.id === n.id) ? null : n; applySelection(); })
    .onBackgroundClick(() => { if (selected) { selected = null; applySelection(); } });

  let selected = null;
  const neighbours = new Set();
  function idOf(x) { return typeof x === 'object' ? x.id : x; }
  function touches(l, n) { return idOf(l.source) === n.id || idOf(l.target) === n.id; }
  function linkIri(l) {
    return l.kind === 'type' ? 'rdf:type' : l.kind === 'sub' ? 'rdfs:subClassOf' : D.usdm + l.p;
  }
  function linkColor(l) {
    if (selected) return touches(l, selected) ? '#F2B441' : 'rgba(180,192,220,0.06)';
    return l.kind === 'inst' ? 'rgba(180,192,220,0.16)'
         : l.kind === 'sub' ? 'rgba(255,255,255,0.6)' : 'rgba(242,180,65,0.10)';
  }
  function nodeColor(n) {
    const base = n.kind === 'hub' ? MODEL_COLOR : FAM_COLOR[n.fam];
    if (!selected) return base;
    if (n.id === selected.id || neighbours.has(n.id)) return base;
    return 'rgba(102,115,143,0.25)';
  }
  function applySelection() {
    neighbours.clear();
    if (selected) {
      Graph.graphData().links.forEach(l => {
        if (idOf(l.source) === selected.id) neighbours.add(idOf(l.target));
        if (idOf(l.target) === selected.id) neighbours.add(idOf(l.source));
      });
    }
    Graph.nodeColor(nodeColor).linkColor(linkColor).linkWidth(Graph.linkWidth());
    document.getElementById('c-pin').hidden = !selected;
    if (selected) onHover(selected); else card.hidden = true;
  }

  Graph.d3Force('charge').strength(n => n.kind === 'hub' ? -220 : -18);
  Graph.d3Force('link').distance(l => l.kind === 'type' ? 22 : l.kind === 'sub' ? 90 : 26)
                       .strength(l => l.kind === 'type' ? 0.9 : l.kind === 'sub' ? 0.6 : 0.35);

  function seedAtOrigin(nodes) {
    nodes.forEach(n => { n.x = (Math.random() - 0.5) * 2; n.y = (Math.random() - 0.5) * 2;
                         n.z = (Math.random() - 0.5) * 2; n.vx = n.vy = n.vz = 0; });
  }
  function refresh(reseed) {
    const d = currentData();
    if (reseed) seedAtOrigin(d.nodes);
    updateShowing(d);
    Graph.graphData(d);
    if (started) Graph.d3ReheatSimulation();
  }
  let started = false;
  seedAtOrigin(instNodes);
  refresh(false);
  started = true;
  const R = 950;
  Graph.cameraPosition({ x: 0, y: 0, z: R });

  // slow orbit until the user takes over
  let orbiting = true, angle = 0;
  const orbit = () => {
    if (orbiting) { angle += 0.0012; Graph.cameraPosition({ x: R * Math.sin(angle), z: R * Math.cos(angle) }); }
    requestAnimationFrame(orbit);
  };
  requestAnimationFrame(orbit);
  el.addEventListener('pointerdown', () => { orbiting = false; }, { once: true });
  el.addEventListener('wheel', () => { orbiting = false; }, { once: true });

  // ---- hub labels (HTML overlay, no extra library) ---------------------------
  const labelLayer = document.createElement('div');
  document.body.appendChild(labelLayer);
  const labelEls = {};
  function tickLabels() {
    if (showModel && showLabels) {
      const d = Graph.graphData();
      d.nodes.forEach(n => {
        if (n.kind !== 'hub' || n.x === undefined) return;
        if (n.count < 3) { if (labelEls[n.id]) labelEls[n.id].hidden = true; return; }
        let e = labelEls[n.id];
        if (!e) { e = document.createElement('div'); e.className = 'hublabel'; e.textContent = 'usdm:' + n.cls; labelLayer.appendChild(e); labelEls[n.id] = e; }
        const s = Graph.graph2ScreenCoords(n.x, n.y, n.z);
        e.style.left = s.x + 'px'; e.style.top = s.y + 'px'; e.hidden = false;
      });
      Object.keys(labelEls).forEach(id => { if (!d.nodes.find(n => n.id === id)) labelEls[id].hidden = true; });
    } else {
      Object.values(labelEls).forEach(e => { e.hidden = true; });
    }
    requestAnimationFrame(tickLabels);
  }
  requestAnimationFrame(tickLabels);

  // ---- hover card --------------------------------------------------------------
  const card = document.getElementById('card');
  function onHover(n) {
    el.style.cursor = n ? 'pointer' : null;
    if (!n) { card.hidden = true; return; }
    const c = D.classes[n.cls];
    const isHub = n.kind === 'hub';
    document.getElementById('c-kind').textContent = isHub ? 'class IRI - resolves' : 'rdf:type - a class IRI that resolves';
    const iri = document.getElementById('c-iri');
    iri.textContent = D.usdm + n.cls; iri.href = D.usdm + n.cls;
    document.getElementById('c-dot').style.background = isHub ? MODEL_COLOR : FAM_COLOR[n.fam];
    document.getElementById('c-cls').textContent = c.label + (isHub ? '  (' + fmt(n.count) + ' instances in this study)' : '');
    document.getElementById('c-pref').textContent = c.prefLabel ? 'preferred term: ' + c.prefLabel : '';
    document.getElementById('c-def').textContent = c.definition;
    const nodeEl = document.getElementById('c-node');
    const nodeLabel = document.getElementById('c-node-label');
    const propsEl = document.getElementById('c-props');
    const propsLabel = document.getElementById('c-props-label');
    if (isHub) {
      nodeLabel.hidden = true; nodeEl.hidden = true; propsLabel.hidden = true; propsEl.hidden = true;
    } else {
      nodeLabel.hidden = false; nodeEl.hidden = false;
      nodeEl.innerHTML = '<b>' + escapeHtml(n.label) + '</b><br>' + escapeHtml(D.base + n.id);
      const counts = {};
      Graph.graphData().links.forEach(l => {
        if (l.kind !== 'inst') return;
        if (idOf(l.source) === n.id) counts[l.p] = (counts[l.p] || 0) + 1;
      });
      const keys = Object.keys(counts).sort();
      propsLabel.hidden = keys.length === 0; propsEl.hidden = keys.length === 0;
      propsEl.innerHTML = keys.map(k => '<a href="' + D.usdm + k + '" target="_blank" rel="noopener"><span>usdm:' + escapeHtml(k) + '</span><span>' + counts[k] + '</span></a>').join('');
    }
    const nc = document.getElementById('c-ncit');
    const ncl = document.getElementById('c-ncit-label');
    if (c.ncit && c.ncit.length) { nc.textContent = c.ncit[0]; nc.href = c.ncit[0]; nc.hidden = false; ncl.hidden = false; }
    else { nc.hidden = true; ncl.hidden = true; }
    card.hidden = false;
  }
  function escapeHtml(s) { return String(s).replace(/[&<>"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch])); }

  // ---- controls ----------------------------------------------------------------
  const bModel = document.getElementById('btn-model');
  const bLabels = document.getElementById('btn-labels');
  bModel.addEventListener('click', () => {
    showModel = !showModel;
    bModel.classList.toggle('on', showModel); bModel.setAttribute('aria-pressed', String(showModel));
    bModel.querySelector('span').textContent = showModel ? 'Hide the model' : 'Show the model';
    if (showModel) seedAtOrigin(hubNodes);
    refresh(false);
  });
  bLabels.addEventListener('click', () => {
    showLabels = !showLabels;
    bLabels.classList.toggle('on', showLabels); bLabels.setAttribute('aria-pressed', String(showLabels));
  });
  document.getElementById('btn-replay').addEventListener('click', () => { refresh(true); orbiting = true; });

  window.addEventListener('resize', () => Graph.width(window.innerWidth).height(window.innerHeight));

  // scripting hook (used for recordings; no effect otherwise)
  window.PilotGraph = {
    graph: Graph,
    node: id => Graph.graphData().nodes.find(n => n.id === id),
    select: id => { selected = id ? Graph.graphData().nodes.find(n => n.id === id) : null; applySelection(); },
    setModel: on => { if (on !== showModel) bModel.click(); },
    setLabels: on => { if (on !== showLabels) bLabels.click(); },
    setFamily: (f, on) => { if (famOn[f] !== on) legend.querySelector('[data-fam="' + f + '"]').click(); },
    replay: () => document.getElementById('btn-replay').click(),
    orbit: on => { orbiting = on; },
    screen: id => { const n = Graph.graphData().nodes.find(x => x.id === id); return n ? Graph.graph2ScreenCoords(n.x, n.y, n.z) : null; }
  };
})();
</script>
"""

html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
out = HERE / "pilot-study-one-graph.html"
out.write_text(html)
print("wrote", out, out.stat().st_size, "bytes")
