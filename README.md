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

## Licence

Code: MIT. Page content derived from CDISC-published files: CC-BY-4.0, as the
DDF-RA source.
