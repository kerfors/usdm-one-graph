"""Build m11/graph.json for "ICH M11 and USDM, coming together".

Five published files are parsed as they are, each into its own graph, in the order
the page loads them:
  1. m11-rdf.ttl          ICH M11 sections and elements (m11-rdf v0.3.0)
  2. usdm_v4.ttl          the USDM v4 model (usdm-rdf v0.7.0)
  3. m11-usdm.sssom.ttl   the HL7 and CDISC M11-to-USDM mapping statements (m11-rdf v0.3.0)
  4. (no new file)        NCIt concepts that 1 and 2 already share
  5. CDISC_Pilot_Study.json, read through usdm_v4.context.jsonld (DDF-RA v4.0.0, usdm-rdf v0.7.0)
Links between files are never computed by matching: they exist because two files use the
same IRI. The one exception is step 6 on the page, which shows on purpose what matching
strings (section numbers, titles) would give where no shared IRI exists.
Every input is fetched from a pinned URL and checked by SHA-256.
"""
import hashlib
import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path

import rdflib
from rdflib.namespace import OWL, RDF, RDFS, SKOS

HERE = Path(__file__).parent
CACHE = HERE / "downloads"

INPUTS = {
    "m11": ("https://raw.githubusercontent.com/kerfors/m11-rdf/v0.3.0/m11-rdf.ttl",
            "1b94d710ebd24d8cb52c5782eff6f62089c2fc31a8bc3264b7e2aa952541a433"),
    "usdm": ("https://raw.githubusercontent.com/kerfors/usdm-rdf/v0.7.0/usdm_v4.ttl",
             "7c6c7b2f79ecc9908a5b7cc7f75011a93245b34c54713d7ee9a19b00dc261deb"),
    "sssom": ("https://raw.githubusercontent.com/kerfors/m11-rdf/v0.3.0/m11-usdm.sssom.ttl",
              "8a00c6af68d4757bb55ee3c769d603ede8824d449ad392ad00f97d0ec8da8344"),
    "context": ("https://raw.githubusercontent.com/kerfors/usdm-rdf/v0.7.0/usdm_v4.context.jsonld",
                "1919be9f0b24b3db80f2e1815f7057cae08b32e9c28b2ad07fecbe65f91694eb"),
    "pilot": ("https://raw.githubusercontent.com/cdisc-org/DDF-RA/v4.0.0/Documents/Examples/CDISC_Pilot/CDISC_Pilot_Study.json",
              "67ab5e35cadc9f900d19403341ec7f89d500aaf692aae328dd3037c31d609aa2"),
}
M11 = rdflib.Namespace("https://w3id.org/m11-rdf/")
USDM = "https://w3id.org/cdisc/usdm/v4/"
SSSOM = rdflib.Namespace("https://w3id.org/sssom/")
BASE_IRI = "https://example.org/studies/CDISC_Pilot/"
OBO = "http://purl.obolibrary.org/obo/NCIT_"


def fetch(key):
    url, sha = INPUTS[key]
    CACHE.mkdir(exist_ok=True)
    path = CACHE / url.rsplit("/", 1)[1]
    if not path.exists():
        with urllib.request.urlopen(url) as r:
            path.write_bytes(r.read())
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    if got != sha:
        raise RuntimeError(f"{path.name}: SHA-256 {got}, expected {sha}")
    return path, url


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


steps = []

# --- 1. ICH M11 -------------------------------------------------------------------------
path, url = fetch("m11")
gm = rdflib.Graph().parse(path, format="turtle")
nodes, links = {}, []
for s in gm.subjects(RDF.type, M11.Section):
    num = gm.value(s, M11.sectionNumber)
    nodes[str(s)] = {"id": str(s), "kind": "section", "step": 1, "label": str(gm.value(s, SKOS.prefLabel)),
                     "num": str(num) if num is not None else "", "heading": str(gm.value(s, M11.templateHeading) or ""),
                     "page": int(gm.value(s, M11.templatePage)) if gm.value(s, M11.templatePage) is not None else None}
    parent = gm.value(s, SKOS.broader)
    if parent is not None:
        links.append({"s": str(s), "t": str(parent), "kind": "tree", "step": 1, "p": "skos:broader"})
for e in gm.subjects(RDF.type, M11.Element):
    fields = [{"label": str(gm.value(f, M11.fieldLabel)), "num": str(gm.value(f, M11.templateSectionNumber)),
               "page": int(gm.value(f, M11.templatePage))} for f in gm.subjects(M11.realises, e)]
    blocks, secs = [], []
    for sp in gm.objects(e, M11.hasSpecification):
        blocks.append(int(gm.value(sp, M11.tsBlock)))
        sec = str(gm.value(sp, M11.inSection))
        if sec not in secs:
            secs.append(sec)
            links.append({"s": str(e), "t": sec, "kind": "place", "step": 1, "p": "m11:inSection (via its specification)"})
    nodes[str(e)] = {"id": str(e), "kind": "element", "step": 1, "label": str(gm.value(e, SKOS.prefLabel)),
                     "definition": str(gm.value(e, SKOS.definition) or ""), "blocks": sorted(blocks), "fields": fields}
steps.append({"file": "m11-rdf.ttl", "url": url, "publisher": "m11-rdf v0.3.0, rendered from ICH M11 (Technical Specification, Template) and the ICH M11 Terminology (NCI EVS)",
              "triples": len(gm), "nodes": sum(1 for n in nodes.values() if n["step"] == 1), "bridges": 0})
print("1:", steps[-1])

# --- 2. USDM v4 model ------------------------------------------------------------------
path, url = fetch("usdm")
gu = rdflib.Graph().parse(path, format="turtle")
for c in gu.subjects(RDF.type, OWL.Class):
    if not str(c).startswith(USDM):
        continue
    nodes[str(c)] = {"id": str(c), "kind": "class", "step": 2, "label": str(c)[len(USDM):],
                     "definition": str(gu.value(c, SKOS.definition) or "")}
    for sup in gu.objects(c, RDFS.subClassOf):
        if str(sup).startswith(USDM):
            links.append({"s": str(c), "t": str(sup), "kind": "sub", "step": 2, "p": "rdfs:subClassOf"})
n_props = sum(1 for _ in gu.subjects(RDF.type, OWL.DatatypeProperty)) + sum(1 for _ in gu.subjects(RDF.type, OWL.ObjectProperty))
steps.append({"file": "usdm_v4.ttl", "url": url, "publisher": "usdm-rdf v0.7.0, rendered from CDISC USDM v4.0.0 (DDF-RA)",
              "triples": len(gu), "nodes": sum(1 for n in nodes.values() if n["step"] == 2), "bridges": 0,
              "note_props": n_props})
print("2:", steps[-1])


def attr_node(a, step):
    """A USDM attribute, drawn when a later file refers to it; attached to its class by usdm-rdf's rdfs:domain."""
    if str(a) in nodes:
        return
    dom = gu.value(a, RDFS.domain)
    if dom is None:
        raise ValueError(f"{a} has no rdfs:domain in usdm_v4.ttl")
    nodes[str(a)] = {"id": str(a), "kind": "attr", "step": step, "label": str(a)[len(USDM):],
                     "definition": str(gu.value(a, SKOS.definition) or "")}
    links.append({"s": str(a), "t": str(dom), "kind": "domain", "step": step, "p": "rdfs:domain (usdm_v4.ttl)"})


# --- 3. mapping statements ------------------------------------------------------------
path, url = fetch("sssom")
gs = rdflib.Graph().parse(path, format="turtle")
pairs = defaultdict(set)
for ax in gs.subjects(RDF.type, OWL.Axiom):
    e, a = gs.value(ax, OWL.annotatedSource), gs.value(ax, OWL.annotatedTarget)
    author = str(gs.value(ax, SSSOM.author_label))
    src = "HL7" if author.startswith("HL7") else "CDISC" if author.startswith("CDISC") else None
    if src is None:
        raise ValueError(f"unknown author {author}")
    if str(e) not in nodes:
        raise ValueError(f"mapping subject {e} is not an element in m11-rdf.ttl")
    pairs[(str(e), str(a))].add(src)
    nodes[str(e)].setdefault("records", []).append({"src": src, "row": int(gs.value(ax, M11.sourceRow)),
                                                   "attr": str(a)[len(USDM):]})
for (e, a), src in pairs.items():
    attr_node(rdflib.URIRef(a), 3)
    links.append({"s": e, "t": a, "kind": "map2" if len(src) == 2 else "map1", "step": 3,
                  "p": "mapped to, stated by " + " and ".join(sorted(src))})
for n in nodes.values():
    if "records" in n:
        n["records"].sort(key=lambda x: (x["src"], x["row"]))
steps.append({"file": "m11-usdm.sssom.ttl", "url": url, "publisher": "the HL7 FHIR Clinical Study Protocol IG ballot mapping (May 2026) and CDISC m11_mapping.xlsx (DDF-RA v4.0.0), as an SSSOM mapping set in m11-rdf",
              "triples": len(gs), "nodes": sum(1 for n in nodes.values() if n["step"] == 3), "bridges": len(pairs),
              "statements": sum(1 for _ in gs.subjects(RDF.type, OWL.Axiom)),
              "both": sum(1 for v in pairs.values() if len(v) == 2), "elements": len({e for e, _ in pairs})})
print("3:", steps[-1])

# --- 4. NCIt concepts files 1 and 2 already share ------------------------------------------
m_side = defaultdict(set)
for e, c in gm.subject_objects(M11.concept):
    if str(c).startswith(OBO) and (e, RDF.type, M11.Element) in gm:
        m_side[str(c)].add(str(e))
u_side = defaultdict(set)
for x, c in gu.subject_objects(SKOS.exactMatch):
    if str(c).startswith(OBO) and str(x).startswith(USDM):
        u_side[str(c)].add(x)
shared = sorted(set(m_side) & set(u_side))
agree = 0
for c in shared:
    nodes[c] = {"id": c, "kind": "concept", "step": 4, "label": "NCIt " + c[len(OBO):]}
    for e in m_side[c]:
        links.append({"s": e, "t": c, "kind": "concept", "step": 4, "p": "m11:concept (m11-rdf.ttl)"})
    for x in u_side[c]:
        if (x, RDF.type, OWL.Class) not in gu:
            attr_node(x, 4)
        links.append({"s": str(x), "t": c, "kind": "concept", "step": 4, "p": "skos:exactMatch (usdm_v4.ttl)"})
        if any((e, str(x)) in pairs for e in m_side[c]):
            agree += 1
            nodes[c]["agrees"] = True
steps.append({"file": None, "url": None, "publisher": "already in files 1 and 2: both anchor their terms to NCIt",
              "triples": 0, "nodes": sum(1 for n in nodes.values() if n["step"] == 4), "bridges": len(shared),
              "agree": agree, "m_concepts": len(m_side), "u_concepts": len(u_side)})
print("4:", steps[-1])

# --- 5. a study, read as it is ------------------------------------------------------------
path, url = fetch("pilot")
document = json.loads(path.read_text())
if document.get("usdmVersion") != "4.0.0":
    raise ValueError(document.get("usdmVersion"))
study = document["study"]
cpath, curl = fetch("context")
study["@context"] = json.loads(cpath.read_text())["@context"]
gp = rdflib.Graph().parse(data=json.dumps(study), format="json-ld", publicID=BASE_IRI)
typed = 0
classes_used = set()
for s, o in gp.subject_objects(RDF.type):
    if not isinstance(s, rdflib.URIRef):
        continue
    if str(o) not in nodes:
        raise ValueError(f"study object typed with {o}, not a class in usdm_v4.ttl")
    nodes[str(s)] = {"id": str(s), "kind": "inst", "step": 5, "label": str(o)[len(USDM):], "cls": str(o)[len(USDM):]}
    links.append({"s": str(s), "t": str(o), "kind": "type", "step": 5, "p": "rdf:type"})
    typed += 1
    classes_used.add(str(o))
# the study's own values for the attributes the mappings name, plus each object's name, so the page can show them
mapped_attrs = {l["t"] for l in links if l["kind"] in ("map1", "map2")}
for k, n in nodes.items():
    if n["kind"] != "inst":
        continue
    vals = {}
    for p, o in gp.predicate_objects(rdflib.URIRef(k)):
        if isinstance(o, rdflib.Literal) and (str(p) in mapped_attrs or str(p).endswith("-name")):
            v = " ".join(str(o).split())
            vals[str(p)[len(USDM):]] = v if len(v) <= 160 else v[:159] + "…"
    if vals:
        n["vals"] = vals
steps.append({"file": "CDISC_Pilot_Study.json", "url": url, "context": curl,
              "publisher": "CDISC (DDF-RA v4.0.0 example), read through the usdm-rdf JSON-LD context",
              "triples": len(gp), "nodes": typed, "bridges": typed, "classes_used": len(classes_used)})
print("5:", steps[-1])

# --- 6. the gap: the study's protocol sections and M11 share no identifier -----------------
sec_by_num = {n["num"]: k for k, n in nodes.items() if n["kind"] == "section" and n["num"]}
sec_by_title = defaultdict(set)
for k, n in nodes.items():
    if n["kind"] != "section":
        continue
    sec_by_title[norm(n["label"].split(" ", 1)[1] if n["num"] else n["label"])].add(k)
    if n["heading"]:
        sec_by_title[norm(n["heading"])].add(k)
P = "PREFIX usdm: <" + USDM + "> "
rows = list(gp.query(P + """
    SELECT ?nc ?num ?title WHERE {
      ?doc usdm:StudyDefinitionDocument-templateName "M11" ; usdm:StudyDefinitionDocument-versions ?ver .
      ?ver usdm:StudyDefinitionDocumentVersion-contents ?nc .
      ?nc usdm:NarrativeContent-sectionNumber ?num ; usdm:NarrativeContent-sectionTitle ?title .
    }"""))
status = defaultdict(int)
for nc, num, title in rows:
    n_sec = sec_by_num.get(str(num).rstrip("."))
    t_secs = sorted(sec_by_title.get(norm(str(title)), set()))
    t_sec = n_sec if n_sec in t_secs else (t_secs[0] if len(t_secs) == 1 else None)
    if len(t_secs) > 1 and t_sec is None:
        st = "title-ambiguous"
    elif n_sec and t_sec:
        st = "agree" if n_sec == t_sec else "differ"
    elif n_sec:
        st = "number-only"
    elif t_sec:
        st = "title-only"
    else:
        st = "neither"
    status[st] += 1
    node = nodes[str(nc)]
    node.update({"kind": "content", "num": str(num), "title": str(title), "status": st,
                 "by_number": n_sec, "by_title": t_sec})
    if n_sec:
        links.append({"s": str(nc), "t": n_sec, "kind": "differ" if st == "differ" else "bynumber", "step": 6,
                      "p": 'string match: section number "' + str(num) + '"'})
    if t_sec and t_sec != n_sec:
        links.append({"s": str(nc), "t": t_sec, "kind": "bytitle", "step": 6, "p": "string match: section title"})
steps.append({"file": None, "url": None, "publisher": "no shared identifier: only strings",
              "triples": 0, "nodes": 0, "bridges": 0, "contents": len(rows), "status": dict(status)})
print("6:", steps[-1])

out = {"m11": str(M11), "usdm": USDM, "base": BASE_IRI, "obo": OBO, "steps": steps,
       "nodes": list(nodes.values()), "links": links}
(HERE / "graph.json").write_text(json.dumps(out, ensure_ascii=False))
print("nodes", len(nodes), "links", len(links), "| written m11/graph.json", (HERE / "graph.json").stat().st_size, "bytes")
