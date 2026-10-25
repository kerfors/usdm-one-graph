"""Lift the CDISC Pilot into an ICH M11 protocol outline, using only the published graphs.

Inputs (the same pinned files as lift_m11.py, each checked by SHA-256):
  m11-rdf.ttl            ICH M11 sections, elements, Template headings and fields (m11-rdf v0.3.1)
  m11-usdm.sssom.ttl     the HL7 and CDISC M11-to-USDM mapping statements (m11-rdf v0.3.1)
  usdm_v4.ttl            the USDM v4 model (usdm-rdf v0.7.0)
  CDISC_Pilot_Study.json read through usdm_v4.context.jsonld (DDF-RA v4.0.0, usdm-rdf v0.7.0)

For each Template field: the element it realises, each mapping statement's USDM attribute, and the
Pilot's values for that attribute, found by a SPARQL query kept with the result. A condition clause is
run only when it tests a code (@code or @decode, = or IN) on the same object as the mapped attribute;
the section-number condition is the mappings' own placement rule. Every other clause is kept as text.
Narrative text is placed by the Pilot's section number (the mappings' rule) and, where the number
finds nothing, by its title (this page's own join, as on the M11 page).
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

# the same pins as lift_m11.py
INPUTS = {
    "m11": ("https://raw.githubusercontent.com/kerfors/m11-rdf/v0.3.1/m11-rdf.ttl",
            "ce48db83279fd1212832fa6e885489ab802e96742bfcbcdfe61cbf822226dca6"),
    "usdm": ("https://raw.githubusercontent.com/kerfors/usdm-rdf/v0.7.0/usdm_v4.ttl",
             "7c6c7b2f79ecc9908a5b7cc7f75011a93245b34c54713d7ee9a19b00dc261deb"),
    "sssom": ("https://raw.githubusercontent.com/kerfors/m11-rdf/v0.3.1/m11-usdm.sssom.ttl",
              "44dada8c4ed414655ebd56935d00d7085af1ac5761df79071cce0f62eaf01430"),
    "context": ("https://raw.githubusercontent.com/kerfors/usdm-rdf/v0.7.0/usdm_v4.context.jsonld",
                "1919be9f0b24b3db80f2e1815f7057cae08b32e9c28b2ad07fecbe65f91694eb"),
    "pilot": ("https://raw.githubusercontent.com/cdisc-org/DDF-RA/v4.0.0/Documents/Examples/CDISC_Pilot/CDISC_Pilot_Study.json",
              "67ab5e35cadc9f900d19403341ec7f89d500aaf692aae328dd3037c31d609aa2"),
}


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


M11 = rdflib.Namespace("https://w3id.org/m11-rdf/")
USDM = "https://w3id.org/cdisc/usdm/v4/"
U = rdflib.Namespace(USDM)
BASE_IRI = "https://example.org/studies/CDISC_Pilot/"
CDISC_CODE_SYSTEM = "http://www.cdisc.org"  # the codeSystem USDM uses for CDISC / NCIt controlled terminology
M11_TEMPLATE = "M11"  # StudyDefinitionDocument.templateName of the study's M11 protocol document
PREFIXES = f"PREFIX usdm: <{USDM}> "

gm = rdflib.Graph().parse(fetch("m11")[0], format="turtle")
gs = rdflib.Graph().parse(fetch("sssom")[0], format="turtle")
gu = rdflib.Graph().parse(fetch("usdm")[0], format="turtle")
document = json.loads(fetch("pilot")[0].read_text())
if document.get("usdmVersion") != "4.0.0":
    raise ValueError(document.get("usdmVersion"))
study = document["study"]
study["@context"] = json.loads(fetch("context")[0].read_text())["@context"]
gp = rdflib.Graph().parse(data=json.dumps(study), format="json-ld", publicID=BASE_IRI)
print(f"m11-rdf {len(gm)}, sssom {len(gs)}, usdm-rdf {len(gu)}, pilot {len(gp)} triples")


def loc(iri, ns):
    s = str(iri)
    if not s.startswith(ns):
        raise ValueError(f"{s} is not under {ns}")
    return s[len(ns):]


# --- usdm-rdf: class chains and property lookup by attribute or role name ----------------------
PROPS = set(gu.subjects(RDF.type, OWL.DatatypeProperty)) | set(gu.subjects(RDF.type, OWL.ObjectProperty))


def chain(cls):
    """The class and its superclasses in usdm-rdf."""
    out, todo = [], [U[cls]]
    while todo:
        c = todo.pop(0)
        if c not in out:
            out.append(c)
            todo.extend(x for x in gu.objects(c, RDFS.subClassOf) if str(x).startswith(USDM))
    return [loc(c, USDM) for c in out]


def prop(cls, name):
    """usdm-rdf property for attribute or role `name` on `cls` or a superclass; None if there is none."""
    if not re.fullmatch(r"\w+", name) or (U[cls], RDF.type, OWL.Class) not in gu:
        return None
    for c in chain(cls):
        p = U[f"{c}-{name}"]
        if p in PROPS:
            return p
        for q in gu.subjects(U.modelName, rdflib.Literal(name)):
            if q in PROPS and (q, RDFS.domain, U[c]) in gu:
                return q
    return None


# --- Pilot values as display text ----------------------------------------------------------------
REF = re.compile(r'<usdm:(ref|tag)\b([^>]*?)(?:/>|>\s*</usdm:\1>)')
ATTR = re.compile(r'(\w+)="([^"]*)"')


def pilot_class(s):
    t = [loc(o, USDM) for o in gp.objects(s, RDF.type)]
    if len(t) != 1:
        raise ValueError(f"{s}: {len(t)} types")
    return t[0]


def resolve(text, owner, trail=()):
    """Resolve usdm:ref (object id + attribute) and usdm:tag (owner's dictionary) in the graph.
    A tag is looked up in the dictionary of the object whose text carries it."""
    def one(m):
        a = dict(ATTR.findall(m.group(2)))
        if m.group(1) == "ref":
            s = rdflib.URIRef(BASE_IRI + a["id"])
            p = prop(a["klass"], a["attribute"])
            vals = list(gp.objects(s, p)) if p else []
            if len(vals) != 1:
                return f'<span class="unres">[ref {a["klass"]} {a["id"]} {a["attribute"]}: {len(vals)} values]</span>'
            return resolve(show(vals[0]), s, trail + (str(s),)) if str(s) not in trail else show(vals[0])
        dct = None
        if owner is not None:
            dp = prop(pilot_class(owner), "dictionary")
            dct = gp.value(owner, dp) if dp else None
        if dct is not None:
            for pm in gp.objects(dct, U["SyntaxTemplateDictionary-parameterMaps"]):
                if str(gp.value(pm, U["ParameterMap-tag"])) == a["name"]:
                    return resolve(str(gp.value(pm, U["ParameterMap-reference"])), owner, trail)
        return f'<span class="unres">[tag {a["name"]}: no dictionary entry]</span>'
    return REF.sub(one, text)


def show(o):
    """A Pilot value as text: literals as they are, codes by decode, other objects by label/name."""
    if isinstance(o, rdflib.Literal):
        return str(o)
    cls = pilot_class(o)
    if cls == "Code":
        return f'{gp.value(o, U["Code-decode"])} ({gp.value(o, U["Code-code"])})'
    if cls == "AliasCode":
        return show(gp.value(o, U["AliasCode-standardCode"]))
    for name in ("label", "name", "text"):
        p = prop(cls, name)
        v = gp.value(o, p) if p else None
        if v is not None and str(v).strip():
            return str(v)
    return loc(o, BASE_IRI)


def codes_on(s, p):
    """The codes an object carries through property p (Code or AliasCode), for showing why a clause keeps it."""
    out = []
    for c in gp.objects(s, p):
        if pilot_class(c) == "AliasCode":
            c = gp.value(c, U["AliasCode-standardCode"])
        out.append({"code": str(gp.value(c, U["Code-code"])), "decode": str(gp.value(c, U["Code-decode"]))})
    return out


# --- condition clauses -------------------------------------------------------------------------------
CODE_CLAUSE = re.compile(r'^(?:.*/)?(?P<cls>\w+)/@(?P<attr>\w+)/Code/@(?P<f>code|decode)\s*'
                         r'(?:=\s*"(?P<v>[^"]*)"|IN\s*\((?P<l>[^)]*)\))\s*$', re.I)


def read_condition(cond, target_cls, hop):
    """Run a code clause on the mapped object (of the class the target path's last hop names, else the
    attribute's domain), or on its parent through the target path's last hop."""
    clauses = []
    for part in [p.strip() for p in cond.split(" | ") if p.strip()]:
        if "sectionNumber" in part:
            clauses.append({"text": part, "kind": "section"})
            continue
        m = CODE_CLAUSE.match(part)
        on = None
        if m and m.group("cls") in chain(hop["cls"] if hop else target_cls):
            on = "s"
        elif m and hop and m.group("cls") in chain(hop["pcls"]):
            on = "parent"
        if on:
            p = prop(m.group("cls"), m.group("attr"))
            if p is None:
                raise ValueError(f"{part}: no usdm-rdf property for {m.group('cls')}.{m.group('attr')}")
            values = [m.group("v")] if m.group("v") is not None else re.findall(r'"([^"]*)"', m.group("l"))
            clauses.append({"text": part, "kind": "run", "on": on, "prop": str(p), "field": m.group("f").lower(), "values": values})
        else:
            clauses.append({"text": part, "kind": "not-run"})
    return clauses


def last_hop(target, attr):
    """The role that reaches the mapped object in the stated target path, when it is stated in plain
    Class/@role/Class/@attribute steps and resolves in usdm-rdf; else None."""
    segs = [x for x in target.split("/") if x]
    for i in range(len(segs) - 1, 2, -1):
        cls, a = segs[i - 1], segs[i]
        if re.fullmatch(r"\w+", cls) and a.startswith("@") and prop(cls, a[1:]) == rdflib.URIRef(attr):
            pcls, role = segs[i - 3], segs[i - 2]
            if re.fullmatch(r"\w+", pcls) and role.startswith("@"):
                q = prop(pcls, role[1:])
                if q is not None:
                    return {"text": f"{pcls}/{role}/{cls}", "prop": str(q), "pcls": pcls, "cls": cls}
            return None
    return None


def run_route(attr, clauses, hop=None):
    """SPARQL for one mapping route; returns the query text, the rows kept and every candidate."""
    run = [c for c in clauses if c["kind"] == "run"]
    lines = [f"  ?s <{attr}> ?v ."]
    if hop:
        lines.append(f"  ?parent <{hop['prop']}> ?s .")
    for i, c in enumerate(run):
        field = "Code-code" if c["field"] == "code" else "Code-decode"
        vals = ", ".join(json.dumps(v) for v in c["values"])
        lines.append(f"  ?{c['on']} <{c['prop']}> ?c{i} . ?c{i} usdm:AliasCode-standardCode?/usdm:{field} ?x{i} . FILTER(?x{i} IN ({vals}))")
    query = "SELECT DISTINCT ?s ?v WHERE {\n" + "\n".join(lines) + "\n}"
    kept = {(str(s), str(v)) for s, v in gp.query(PREFIXES + query)}
    cands = []
    for s, v in sorted(gp.subject_objects(rdflib.URIRef(attr)), key=lambda x: (str(x[0]), str(x[1]))):
        k = (str(s), str(v)) in kept
        val = resolve(show(v), s)
        if not k:
            val = " ".join(re.sub(r"<[^>]+>", " ", val).split())
            val = val if len(val) <= 240 else val[:239] + "…"
        parents = list(gp.subjects(rdflib.URIRef(hop["prop"]), s)) if hop else []
        cands.append({"s": str(s), "cls": pilot_class(s), "value": val, "kept": k,
                      "via": [loc(x, BASE_IRI) for x in parents],
                      "codes": [{"clause": c["text"], "on": c["on"],
                                 "codes": [x for o in ([s] if c["on"] == "s" else parents) for x in codes_on(o, rdflib.URIRef(c["prop"]))]}
                                for c in run]})
    return query, cands


def tidy(q):
    return re.sub(r"<" + re.escape(USDM) + r"([^>]+)>", r"usdm:\1", q)


# --- the Pilot's M11 document -------------------------------------------------------------------------
P = PREFIXES
pilot_sections = []
for nc, num, title, nci in gp.query(P + """
    SELECT ?nc ?num ?title ?nci WHERE {
      ?doc usdm:StudyDefinitionDocument-templateName ?tn ; usdm:StudyDefinitionDocument-versions ?ver .
      ?ver usdm:StudyDefinitionDocumentVersion-contents ?nc .
      ?nc usdm:NarrativeContent-sectionNumber ?num ; usdm:NarrativeContent-sectionTitle ?title .
      OPTIONAL { ?nc usdm:NarrativeContent-contentItemId ?nci }
    }""", initBindings={"tn": rdflib.Literal(M11_TEMPLATE)}):
    text = None
    if nci is not None:
        t = gp.value(nci, U["NarrativeContentItem-text"])
        text = resolve(str(t), nci) if t is not None else None
    pilot_sections.append({"iri": str(nc), "num": str(num), "title": str(title),
                           "item": str(nci) if nci is not None else None, "text": text, "shared": []})
if not pilot_sections:
    raise ValueError(f"no StudyDefinitionDocument with templateName {M11_TEMPLATE!r} and sections")

# the same NarrativeContentItem used by a section of another document (or another section): a join by identifier
by_iri = {ps["iri"]: ps for ps in pilot_sections}
for nc, nc2, tn, num2, title2 in gp.query(P + """
    SELECT DISTINCT ?nc ?nc2 ?tn ?num2 ?title2 WHERE {
      ?nc usdm:NarrativeContent-contentItemId ?nci .
      ?nc2 usdm:NarrativeContent-contentItemId ?nci .
      FILTER(?nc2 != ?nc)
      ?ver2 usdm:StudyDefinitionDocumentVersion-contents ?nc2 .
      ?doc2 usdm:StudyDefinitionDocument-versions ?ver2 ; usdm:StudyDefinitionDocument-templateName ?tn .
      ?nc2 usdm:NarrativeContent-sectionNumber ?num2 ; usdm:NarrativeContent-sectionTitle ?title2 .
    }"""):
    if str(nc) in by_iri:
        by_iri[str(nc)]["shared"].append({"iri": str(nc2), "template": str(tn), "num": str(num2), "title": str(title2)})
for ps in pilot_sections:
    ps["shared"].sort(key=lambda x: (x["template"], x["num"]))

# identical text under a different content item, in any section of any document: string matching, labelled as such
by_text = defaultdict(list)
for nc, nci, t, tn, num2, title2 in gp.query(P + """
    SELECT ?nc ?nci ?t ?tn ?num ?title WHERE {
      ?nc usdm:NarrativeContent-contentItemId ?nci ; usdm:NarrativeContent-sectionNumber ?num ; usdm:NarrativeContent-sectionTitle ?title .
      ?nci usdm:NarrativeContentItem-text ?t .
      ?ver usdm:StudyDefinitionDocumentVersion-contents ?nc .
      ?doc usdm:StudyDefinitionDocument-versions ?ver ; usdm:StudyDefinitionDocument-templateName ?tn .
    }"""):
    by_text[str(t)].append({"iri": str(nc), "item": str(nci), "template": str(tn), "num": str(num2), "title": str(title2)})
for ps in pilot_sections:
    ps["copies"] = []
    if ps["item"] is None:
        continue
    t = gp.value(rdflib.URIRef(ps["item"]), U["NarrativeContentItem-text"])
    if t is not None and str(t).strip():
        ps["copies"] = sorted((x for x in by_text[str(t)] if x["item"] != ps["item"]), key=lambda x: (x["template"], x["num"]))

# --- M11 sections, Template headings and fields ------------------------------------------------------
sections = {}
for s in gm.subjects(RDF.type, M11.Section):
    num = gm.value(s, M11.sectionNumber)
    page = gm.value(s, M11.templatePage)
    sections[str(s)] = {"iri": str(s), "label": str(gm.value(s, SKOS.prefLabel)), "num": str(num) if num is not None else "",
                        "heading": str(gm.value(s, M11.templateHeading) or ""), "page": int(page) if page is not None else None,
                        "optional": str(gm.value(s, M11.templateOptional)) == "true",
                        "conditional": str(gm.value(s, M11.templateConditional)) == "true",
                        "heading_element": str(gm.value(s, M11.headingElement) or ""),
                        "fields": [], "pilot": [], "notes": []}

records = defaultdict(list)
for ax in gs.subjects(RDF.type, OWL.Axiom):
    author = str(gs.value(ax, rdflib.URIRef("https://w3id.org/sssom/author_label")))
    src = "HL7" if author.startswith("HL7") else "CDISC" if author.startswith("CDISC") else None
    if src is None:
        raise ValueError(author)
    records[str(gs.value(ax, OWL.annotatedSource))].append({
        "src": src, "row": int(gs.value(ax, M11.sourceRow)), "iri": str(ax) if isinstance(ax, rdflib.URIRef) else None,
        "attr": str(gs.value(ax, OWL.annotatedTarget)), "cls": str(gs.value(ax, M11.statedClass)),
        "cond": " ".join(str(gs.value(ax, M11.conditionPath) or "").split()),
        "target": " ".join(str(gs.value(ax, M11.targetPath) or "").split())})

route_cache = {}
for s, sec in sections.items():
    for f in gm.objects(rdflib.URIRef(s), M11.hasTemplateField):
        e = gm.value(f, M11.realises)
        field = {"label": str(gm.value(f, M11.fieldLabel)), "order": int(gm.value(f, M11.templateOrder)),
                 "page": int(gm.value(f, M11.templatePage)), "kind": loc(gm.value(f, M11.fieldKind), str(M11)),
                 "optional": str(gm.value(f, M11.templateOptional)) == "true",
                 "conditional": str(gm.value(f, M11.templateConditional)) == "true",
                 "element": None, "routes": []}
        if e is not None:
            field["element"] = {"iri": str(e), "label": str(gm.value(e, SKOS.prefLabel)),
                                "code": str(gm.value(e, M11.ichConceptCode))}
            groups = defaultdict(list)
            for r in records.get(str(e), []):
                hop = last_hop(r["target"], r["attr"])
                groups[(r["attr"], r["cond"], json.dumps(hop))].append(r)
            for (attr, cond, hopj), rs in sorted(groups.items()):
                hop = json.loads(hopj)
                target_cls = loc(gu.value(rdflib.URIRef(attr), RDFS.domain), USDM)
                clauses = read_condition(cond, target_cls, hop) if cond else []
                route = {"attr": loc(attr, USDM), "cond": cond, "hop": hop["text"] if hop else None,
                         "clauses": [{k: c.get(k) for k in ("text", "kind", "on")} for c in clauses],
                         "sources": sorted({(r["src"], r["row"]) for r in rs}), "targets": sorted({r["target"] for r in rs})}
                if any(c["kind"] == "section" for c in clauses):
                    route["status"] = "section-rule"
                else:
                    key = (attr, cond, hopj)
                    if key not in route_cache:
                        route_cache[key] = run_route(attr, clauses, hop)
                    query, cands = route_cache[key]
                    kept = [c for c in cands if c["kept"]]
                    route.update({"query": tidy(query), "candidates": cands, "n_kept": len(kept), "n_all": len(cands),
                                  "status": ("none" if not cands else "one" if len(kept) == 1 else
                                             "filtered-out" if not kept else "several")})
                    if any(c["kind"] == "not-run" for c in clauses) and route["status"] in ("one", "several"):
                        route["status"] = "not-checked"
                field["routes"].append(route)
        sec["fields"].append(field)
    sec["fields"].sort(key=lambda x: x["order"])

# --- place the Pilot's sections: by number (the mappings' rule), else by title (this page's join) -----------
by_num = {v["num"]: k for k, v in sections.items() if v["num"]}
by_title = defaultdict(set)
for k, v in sections.items():
    by_title[norm(v["label"].split(" ", 1)[1] if v["num"] else v["label"])].add(k)
    if v["heading"]:
        by_title[norm(v["heading"])].add(k)
unplaced = []
for ps in pilot_sections:
    n = by_num.get(ps["num"].rstrip("."))
    ts = sorted(by_title.get(norm(ps["title"]), set()))
    t = n if n in ts else (ts[0] if len(ts) == 1 else None)
    ps["by_number"], ps["by_title"] = n, t
    ps["status"] = ("title-ambiguous" if len(ts) > 1 and t is None else "agree" if n and n == t else
                    "differ" if n and t else "number-only" if n else "title-only" if t else "neither")
    if n:
        sections[n]["pilot"].append({**ps, "placed_by": "number"})
        if t and t != n:
            sections[t]["notes"].append({"iri": ps["iri"], "num": ps["num"], "title": ps["title"], "at": n})
    elif t:
        sections[t]["pilot"].append({**ps, "placed_by": "title"})
    else:
        unplaced.append(ps)


def nkey(num):
    return [int(x) if x.isdigit() else x for x in re.split(r"[.]", num)] if num else []


for v in sections.values():
    if v["page"] is None:
        if not v["fields"]:
            raise ValueError(f"{v['iri']}: no Template page and no fields")
        v["page"] = min(f["page"] for f in v["fields"])
order = sorted(sections.values(), key=lambda v: (v["page"], v["num"] != "", nkey(v["num"])))
# --- codes the study puts in the CDISC code system that are not of the NCIt form C<digits> ---------------
odd_codes = defaultdict(lambda: {"decode": set(), "attrs": set(), "n": 0})
for c, code, decode in gp.query(P + """
    SELECT ?c ?code ?decode WHERE {
      ?c a usdm:Code ; usdm:Code-code ?code ; usdm:Code-decode ?decode ; usdm:Code-codeSystem ?cs .
      FILTER(!REGEX(STR(?code), "^C[0-9]+$"))
    }""", initBindings={"cs": rdflib.Literal(CDISC_CODE_SYSTEM)}):
    g = odd_codes[str(code)]
    g["decode"].add(str(decode))
    g["n"] += 1
    for holder, p_ in gp.subject_predicates(c):
        if str(p_).startswith(USDM):
            g["attrs"].add(loc(p_, USDM))
codes = [{"code": k, "decode": sorted(g["decode"]), "attrs": sorted(g["attrs"]), "n": g["n"]} for k, g in sorted(odd_codes.items())]
print("CDISC-system codes not of the form C<digits>:", [(c["code"], c["n"]) for c in codes])

out = {"m11": str(M11), "usdm": USDM, "base": BASE_IRI, "sections": order, "unplaced": unplaced, "codes": codes,
       "inputs": {k: v[0] for k, v in INPUTS.items()},
       "triples": {"m11": len(gm), "usdm": len(gu), "sssom": len(gs), "pilot": len(gp)}}
(HERE / "protocol.json").write_text(json.dumps(out, ensure_ascii=False))

# --- counts for the page text and the README --------------------------------------------------------
fields = [f for s in order for f in s["fields"]]
rstat = defaultdict(int)
for f in fields:
    for r in f["routes"]:
        rstat[r["status"]] += 1
print("Pilot sections with identical text under another content item:", [(p["num"], [(x["template"], x["num"], x["item"][len(BASE_IRI):]) for x in p["copies"]]) for p in pilot_sections if p["copies"]])
print("Pilot sections sharing a content item with another section:", sum(1 for p in pilot_sections if p["shared"]),
      [(p["num"], [(x["template"], x["num"]) for x in p["shared"]]) for p in pilot_sections if p["shared"]])
print("sections", len(order), "| with Pilot section placed", sum(1 for s in order if s["pilot"]),
      "| with Pilot text", sum(1 for s in order if any(p["text"] for p in s["pilot"])), "| unplaced", len(unplaced))
print("fields", len(fields), "| realising an element", sum(1 for f in fields if f["element"]),
      "| with a mapping route", sum(1 for f in fields if f["routes"]), "| routes by status", dict(rstat),
      "| with a last hop", sum(1 for f in fields for r in f["routes"] if r["hop"]))
print("written m11/protocol.json", (HERE / "protocol.json").stat().st_size, "bytes")
