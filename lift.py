import json
from pathlib import Path

import rdflib
from rdflib.namespace import OWL, RDF, RDFS, SKOS

UP = Path("/mnt/user-data/uploads/usdm-rdf")
STUDY_JSON = UP / "downloads/CDISC_Pilot_Study.json"
CONTEXT_PATH = UP / "usdm_v4.context.jsonld"
TTL_PATH = UP / "usdm_v4.ttl"
BASE_IRI = "https://example.org/studies/CDISC_Pilot/"
USDM = "https://w3id.org/cdisc/usdm/v4/"

document = json.loads(STUDY_JSON.read_text())
if document.get("usdmVersion") != "4.0.0":
    raise ValueError(document.get("usdmVersion"))
study = document["study"]
context = json.loads(CONTEXT_PATH.read_text())["@context"]

study["@context"] = context
instances = rdflib.Graph()
instances.parse(data=json.dumps(study), format="json-ld", publicID=BASE_IRI)
print("instance triples:", len(instances))

ontology = rdflib.Graph()
ontology.parse(str(TTL_PATH), format="turtle")
print("model triples:", len(ontology))

# --- model lookups -----------------------------------------------------------
classes = {}
for c in ontology.subjects(RDF.type, OWL.Class):
    if not str(c).startswith(USDM):
        continue
    name = str(c)[len(USDM):]
    classes[name] = {
        "iri": str(c),
        "label": str(ontology.value(c, RDFS.label) or name),
        "prefLabel": str(ontology.value(c, SKOS.prefLabel) or ""),
        "definition": str(ontology.value(c, SKOS.definition) or ""),
        "ncit": sorted(
            str(o) for o in ontology.objects(c, SKOS.exactMatch)
            if "obolibrary" in str(o)
        ),
        "superclass": [
            str(o)[len(USDM):] for o in ontology.objects(c, RDFS.subClassOf)
            if str(o).startswith(USDM)
        ],
    }
print("model classes:", len(classes))

prop_label = {}
for p in list(ontology.subjects(RDF.type, OWL.ObjectProperty)) + list(
    ontology.subjects(RDF.type, OWL.DatatypeProperty)
):
    prop_label[str(p)] = str(p)[len(USDM):]

# --- nodes ------------------------------------------------------------------
nodes = {}
for s, o in instances.subject_objects(RDF.type):
    if not isinstance(s, rdflib.URIRef):
        continue
    cls = str(o)[len(USDM):]
    if cls not in classes:
        raise ValueError(f"instance typed with unknown class {o}")
    nid = str(s)[len(BASE_IRI):]
    nodes[str(s)] = {"id": nid, "cls": cls, "label": None}

# a display label: name > label > text > id
LABEL_PROPS = ["name", "label", "text", "instanceType"]
for s, node in nodes.items():
    subj = rdflib.URIRef(s)
    for attr in LABEL_PROPS:
        for p, o in instances.predicate_objects(subj):
            if isinstance(o, rdflib.Literal) and str(p).endswith("-" + attr):
                node["label"] = str(o)[:80]
                break
        if node["label"]:
            break
    if not node["label"]:
        node["label"] = node["id"]

# --- edges (object links only, typed nodes on both ends) ----------------------
edges = []
for s, p, o in instances:
    if p == RDF.type:
        continue
    if isinstance(o, rdflib.URIRef) and str(s) in nodes and str(o) in nodes:
        edges.append({"s": nodes[str(s)]["id"], "t": nodes[str(o)]["id"],
                      "p": prop_label.get(str(p), str(p))})
print("nodes:", len(nodes), "edges:", len(edges))

# literal counts per node (for node size)
lit = {}
for s, p, o in instances:
    if isinstance(o, rdflib.Literal) and str(s) in nodes:
        lit[str(s)] = lit.get(str(s), 0) + 1
for s, node in nodes.items():
    node["lit"] = lit.get(s, 0)

# class census
census = {}
for node in nodes.values():
    census[node["cls"]] = census.get(node["cls"], 0) + 1
print("classes used:", len(census))
for k, v in sorted(census.items(), key=lambda kv: -kv[1])[:12]:
    print(f"  {v:5d}  {k}")

out = {
    "base": BASE_IRI,
    "usdm": USDM,
    "study_title": next(
        (str(o) for s, p, o in instances
         if str(p) == USDM + "StudyTitle-text"), ""),
    "stats": {"instance_triples": len(instances), "nodes": len(nodes),
              "edges": len(edges), "classes_used": len(census),
              "classes_model": len(classes)},
    "classes": {k: classes[k] for k in census},
    "census": census,
    "nodes": list(nodes.values()),
    "edges": edges,
}
Path("graph.json").write_text(json.dumps(out, ensure_ascii=False))
print("written graph.json", Path("graph.json").stat().st_size, "bytes")
