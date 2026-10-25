# usdm-one-graph

CDISC's pilot study definition (USDM v4, `CDISC_Pilot_Study.json` from
[cdisc-org/DDF-RA](https://github.com/cdisc-org/DDF-RA) v4.0.0) read through the
[usdm-rdf](https://github.com/kerfors/usdm-rdf) JSON-LD context and drawn as one
interactive 3D graph.

Live page: https://kerfors.github.io/usdm-one-graph/

- 11,811 statements, 1,952 typed objects, 3,206 links, 57 of the model's 80
  concrete classes used. Numbers are the v0.7.0 lift, identical to
  `notebooks/60_validate_study.ipynb` in usdm-rdf.
- "Show the model" adds the class IRIs as nodes; the objects cluster around them.
- Every class and attribute IRI shown resolves at https://w3id.org/cdisc/usdm/v4/.
- The colour families (terminology, narrative, biomedical concepts, schedule,
  eligibility, design) are a hand-made grouping for the picture, not part of the
  model.

## How it was made

`lift.py` lifts the study JSON with rdflib (BASE_IRI is a placeholder namespace;
instance IRIs do not resolve) and writes `graph.json`; `build_html.py` inlines that
into `index.html`. The page loads one pinned library,
[3d-force-graph 1.73.4](https://github.com/vasturiano/3d-force-graph), from
jsDelivr.

This is a demonstration for the article *One graph, three articles - a summer
recap*, not a deliverable of usdm-rdf.

## Second page: ICH M11 and USDM, coming together

Live page: https://kerfors.github.io/usdm-one-graph/m11/

Published files about ICH M11 and USDM v4, loaded one at a time and as they are, in
seven steps (the last in two parts, 7a and 7b). Where two files use the same identifier, they join by themselves; where they
only share text, you are back to matching strings.

1. `m11-rdf.ttl` ([m11-rdf](https://github.com/kerfors/m11-rdf) v0.3.0): ICH M11
   sections and elements, one island.
2. `usdm_v4.ttl` (usdm-rdf v0.7.0): the USDM v4 model, a second island.
3. `m11-usdm.sssom.ttl` (m11-rdf v0.3.0): the HL7 and CDISC M11-to-USDM mapping
   statements; 224 links appear between the islands, because each statement names both
   identifiers. 210 are stated by both CDISC and HL7, 14 by only one (11 HL7, 3 CDISC).
4. NCIt: 10 concepts both files already share, so 10 links were there all along.
5. The study's definitions: `CDISC_Pilot_Study.json` (DDF-RA v4.0.0), read through the
   usdm-rdf JSON-LD context; 1,952 objects attach to their 57 USDM classes.
6. The study's protocol: the same file holds 155 protocol sections. Each has a section
   number and a title, as text, and no ICH M11 identifier, so nothing links them.
7. a. Protocol sections → ICH M11 sections: the only way is to match the number and
   title strings. 87 land on the same M11 section by both, 16 on two different ones,
   52 on one or none.
   b. Protocol sections → the study's definitions: from the 87, the step 3 mappings
   carry on. 38 M11 elements reach 25 specific USDM attributes and the study objects
   that hold them; 118 reach only `NarrativeContentItem.text`, generic text that does
   not say what it is. Hovering a section shows the study's own values. Where the
   attribute belongs to an abstract class (`SyntaxTemplate-text`), the values are held
   by several classes, and the mapping does not say which.

   With M11 section identifiers in the study's definitions, 7a and 7b would be links
   like step 3; that is left as a question for USDM 4.1.

`index.html?step=3` opens a given step; the last step links to the third page.

The example study is not fully consistent or populated; it is used because it is real.
Every M11, USDM and NCIt identifier shown resolves.

`m11/lift_m11.py` fetches the inputs from pinned URLs (checked by SHA-256), parses each
file into its own graph and writes `m11/graph.json`, including the study's values for
the attributes the mappings name; links between files come only from
shared IRIs, except the string matching of step 7a, which is shown on purpose.
`m11/build_m11_html.py` inlines that into `m11/index.html`.

## Third page: the CDISC Pilot as an ICH M11 protocol

Live page: https://kerfors.github.io/usdm-one-graph/m11/protocol.html

The same published files, used to lay the pilot study out as an ICH M11 protocol. The
outline is the ICH M11 Template as m11-rdf renders it: 160 headings and 281 fields in
Template order. Each field's value is found by a SPARQL query over the study's graph,
following the HL7 and CDISC mapping statements from the M11 element to its USDM
attribute. Clicking a field shows how: the element, the mapping rows, the attribute,
the condition, the query and every candidate value with the codes it carries.

Where the example study's data does not fit the mapping, the page says where and why
instead of failing or leaving a blank. Full Title, for example, is mapped to the
`StudyTitle` whose type is C207616; the study types its titles with placeholder codes
(`C99905x1`, `x2`, `x3`), so the condition finds nothing, and all four titles are shown
with their codes. Of the 281 fields, 16 get one value, 53 show such an oddity, 140 are
narrative text placed by section number, 6 are mapped to an attribute the study does
not fill, and 66 have no mapping statement or no M11 element.

A list at the top of the page, "Where the Pilot and the mappings do not fit", opened from
the oddity counter, groups the same results: what each mapping condition asks for and
what the study carries instead, codes the study puts in the CDISC code system that are
not of the form C<digits> (`C99905x1`, "No Concept Code", ...), and text the study holds
twice. The study's two protocol documents share no content item; five M11 sections
hold identical copies of the other document's text under different identifiers, found
by comparing the text and labelled as such.

The page has two views, switched at the top of the side panel. "Protocol" (the
default) shows only the protocol: the Template headings, the study's text, and the
fields where the queries find one value or several values; every other field is shown
as the Template's grey placeholder, `<…>` or `[…]`. "Deep dive" (`protocol.html?view=deep`)
is the page described above, with the colours, the oddity list and how each value was
found. Clicking a field in the protocol view opens the deep dive at that field.
Headings the Template repeats (<#>) are repeated per objective, numbered by the study's
identifiers. In the deep dive each route starts with its hops between identifiers,
numbered by the steps of the second page; a side-panel block lists the files behind the
page.

The scripts contain no codes or values from the study. Two readings are the page's own
and are stated on it: a condition clause is run only when it tests a code on the mapped
object or on its parent through the target path's last hop, and a value is not shown
as filled while any clause of its condition is not run. Narrative text is placed by
the study's section number (the mappings' own rule) and otherwise by its title, as on
the second page.

`m11/lift_protocol.py` uses the same pinned inputs as `m11/lift_m11.py` and writes
`m11/protocol.json`; `m11/build_protocol_html.py` inlines that into
`m11/protocol.html`.

## Licence

Code: MIT. Page content derived from CDISC-published files: CC-BY-4.0, as the
DDF-RA source. The M11 page also carries content derived from ICH M11 (© ICH,
used under the ICH Legal Mentions) and the ICH M11 Terminology (NCI EVS, CC BY 4.0),
as m11-rdf does.
