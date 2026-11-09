---
name: answer-eye-questions-with-visionkb-kg
description: Answer chat-style knowledge questions about eye genes, cell types, diseases and datasets from the VisionKB knowledge graph through its read-only HTTP API or the equivalent visionkb-kg MCP tools, citing the KG release and dataset versions. Resolves a gene or cell type to a CURIE, reads per-class and per-cell-type expression from the HECA atlas summaries, reads typed Biolink relationships with knowledge_level, sources and PMIDs, opens the evidence behind an edge, and finds atlases with ready bind records, keeping atlas observations apart from curated claims. Use for questions such as which retinal cell types express LRAT, which class has the highest RHO, which diseases and PMIDs are recorded for PRPF31, or which atlases contain RPE cells. Not for new analysis of cell-level data.
license: MIT
compatibility: Needs network access to a running VisionKB API (visionkb-api 0.1.1 or later, deployed with visionkb-deploy) and a read token in a file; Python 3.11+ with httpx, or curl and jq. No local compute, no atlas files, no scheduler.
metadata:
  category: knowledge-graph
  version: "0.0.1"
  status: community
  author: "Jin Li"
  tags: "knowledge-graph, biolink, gene-expression, retina, eye, cell-atlas, disease-genes, provenance, rest-api, mcp"
  tested-with: "TBD (pending the run on the real release)"
  compute: "TBD (pending the run on the real release)"
  requires-gpu: "false"
  scheduler: "none"
  requires-network: "runtime"
  requires-secrets: "VISIONKB_API_TOKEN_FILE"
---

# Answer eye knowledge questions with the VisionKB knowledge graph

VisionKB is a Biolink 4.4.6 knowledge graph of eye biology: HGNC genes, Cell Ontology cell types
plus dataset-specific cell states, UBERON tissues, MONDO diseases, HPO phenotypes, the 13 Human
Eye Cell Atlas (HECA) single-cell and single-nucleus atlases as datasets, expression edges derived
from those atlases, and curated gene-disease claims. It is served read-only by
[visionkb-api](https://github.com/lijinbio/visionkb-api) (deployment:
[visionkb-deploy](https://github.com/lijinbio/visionkb-deploy)) and released as immutable,
versioned bundles (`kg_release` = `visionkb-YYYY.MM.N`).

This skill is the **knowledge answer** route: a few API calls (seconds), no atlas files opened, no
jobs. Every response carries `kg_release`; every expression row carries `dataset_id` and
`dataset_version`. Cite both.

Tested end to end, as written, against a stack deployed with visionkb-deploy 0.1.1 on an HPC
compute node, serving the first real release TBD (pending the run on the real release).

Replace every `/path/to/...` with your own values.

## When to use

- "Which cell types / major classes express gene X, how strongly, with how many donors?"
- "Which class has the highest X?" (ranked atlas summaries).
- "What is known about gene X and disease Y, with PMIDs?" (curated `gene_associated_with_condition`).
- "Which genes are associated with disease Y?", "Which genes are expressed in cell type Z?" (gene sets).
- "Which atlases contain RPE cells / are from retina, and how do I attach one?" (registry + bind record).
- Before a Route B/C analysis: pick the dataset and prior evidence to compare against.

## When NOT to use

- New statistics on cell-level data (DE, composition, signature scoring, donor-aware tests): bind
  the atlas the registry returns and run the analysis tools; the KG holds summaries only.
- Region-specific claims from the graph: region x class numbers exist only in the atlas summary
  table (`level=region_majorclass`), never as edges.
- Perturbation results and cell-state comparisons: not in release v0.1 (the API does not expose them).

## 1. Environment

```bash
mamba create -y -n visionkb_kgclient -c conda-forge python=3.13 httpx=0.28.1 jq curl
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate visionkb_kgclient
export VISIONKB_API_URL=http://127.0.0.1:8770/v1                 # your deployment
export VISIONKB_API_TOKEN_FILE=/path/to/secrets/api_token_read   # one line: the read token
```

The tested solve: TBD (pending the run on the real release). With visionkb-deploy, `bin/visionkb init` writes the read
token to `<deploy dir>/<instance>/secrets/api_token_read` (mode 600) and `bin/visionkb health`
checks the stack. Never paste the token into code, logs or reports.

## 2. Client

Every call returns the same envelope:
`{"status": "ok"|"error", "kg_release", "data", "page": {"limit", "offset", "total"} | null, "warnings", "error"}`.
Lists default to 50 rows (max 200); page with `offset`. Errors are returned as envelopes, never as
invented data. The helper below raises on `status: error`, prints `warnings`, keeps every
envelope as JSON for the report, and resolves names only on an exact CURIE or symbol match:

```python
import json
import os
import pathlib
import sys

import httpx

API = os.environ["VISIONKB_API_URL"]  # e.g. http://127.0.0.1:8770/v1
TOKEN = pathlib.Path(os.environ["VISIONKB_API_TOKEN_FILE"]).read_text().strip()
kg = httpx.Client(base_url=API, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=60)
OUT = pathlib.Path(sys.argv[1])  # every response envelope is kept here, for the report
OUT.mkdir(parents=True, exist_ok=True)
SEQ = [0]


def get(path, **params):
    """GET one endpoint; return the envelope. Raise on status=error; print warnings."""
    r = kg.get(path, params=params)
    env = r.json()
    if env["status"] != "ok":
        raise RuntimeError(f"{path} {r.status_code}: {env['error']}")
    for w in env["warnings"]:
        print("  warning:", w)
    return env


def resolve(q, category="biolink:Gene"):
    """search_entities, keeping only exact CURIE / symbol matches; fail loudly otherwise."""
    env = get("/entities/search", q=q, category=category, limit=5)
    exact = [h for h in env["data"] if h["match"] in ("exact_id", "exact_symbol")]
    if len(exact) != 1:
        raise LookupError(f"{q}: {len(exact)} exact matches in {env['kg_release']}: {env['data']}")
    return exact[0]["id"], env


def save(name, env):
    SEQ[0] += 1
    (OUT / f"{SEQ[0]:02d}_{name}.json").write_text(json.dumps(env, indent=1))


def show(rows, cols):
    for r in rows:
        print("  " + "  ".join(f"{c}={r.get(c)}" for c in cols))
```

The same calls with curl and jq (these ran as written):

```bash
H="Authorization: Bearer $(cat "$VISIONKB_API_TOKEN_FILE")"
curl -fsS "$VISIONKB_API_URL/ready" >ready.json
curl -fsS -H "$H" "$VISIONKB_API_URL/entities/search?q=LRAT&category=biolink:Gene&limit=3" >search.json
curl -fsS -H "$H" "$VISIONKB_API_URL/atlas/expression?genes=LRAT&level=majorclass&limit=3" >atlas.json
jq -c '{kg_release, ready: .data}' ready.json
jq -c '.kg_release, (.data[] | {id, symbol, match})' search.json
jq -c '.data[] | {dataset_id, dataset_version, group_label, pct_expressing, pseudobulk_cp10k}' atlas.json
# errors are envelopes too: no token -> 401; no subject/object -> 400 missing_anchor
curl -sS -o /dev/null -w 'no token: HTTP %{http_code}\n' "$VISIONKB_API_URL/release"
curl -sS -H "$H" "$VISIONKB_API_URL/relationships?predicate=biolink:expressed_in" | jq -c '{status, error}'
```

TBD (pending the run on the real release)

## 3. What is in the graph, and what each field means

| Source | Edges | `knowledge_level` | `agent_type` | `primary_knowledge_source` |
| --- | --- | --- | --- | --- |
| HECA atlas summaries | `expressed_in` (gene -> cell type or state) | `observation` | `data_analysis_pipeline` | `infores:visionkb-heca` |
| RetiGene curated review | `gene_associated_with_condition` (gene -> disease) | `knowledge_assertion` | `manual_validation_of_automated_agent` | `infores:visionkb-retigene` |
| CL, UBERON, MONDO, HPO | `subclass_of`, `part_of` | `knowledge_assertion` | `manual_agent` | `infores:cl`, ... |

`knowledge_level` is what keeps observations apart from claims: an `expressed_in` edge says "this
transcript was measured in these cells of this atlas", nothing about function; a
`gene_associated_with_condition` edge is a curated statement backed by publications. Filter with
`knowledge_level=` on `/relationships` and report the two kinds in separate paragraphs.

**Evidence.** Each edge lists `has_study_results`; `GET /evidence/{edge_id}` returns them. For
expression, one StudyResult per (dataset, level, group) with `n_cells`, `n_donors`,
`pct_expressing`, `mean_log1p_cp10k`, `pseudobulk_cp10k`, `n_donors_expressing`, `method`; for
curated claims, `pmid`, `grade`, `review_note` and a short `supporting_text`.

**What makes an `expressed_in` edge (VisionKB decision D18).** A (gene, dataset, group) becomes an
edge, with a StudyResult, only if all of these hold:

1. `pct_expressing >= 0.10` and `n_cells >= 20` in the group;
2. `pseudobulk_cp10k >= 0.10 x` the gene's maximum over the groups of the same dataset and level
   (specificity: removes low-level spill-over of very abundant transcripts);
3. `n_donors_expressing >= 2` (a donor counts when >= 10 % of its cells in the group express the
   gene). Atlases without donor labels use 1-2 only and their edges are flagged.

Edges exist at two levels, `majorclass` and `celltype` (CL class, or a `visionkb:cs-<dataset>-<label>`
CellState that is `subclass_of` a CL class). **Region x major class numbers are only in the
Parquet summaries** (`/atlas/expression?level=region_majorclass`); there are no regional edges.

**Absence of an edge is not evidence of non-expression.** The graph keeps only the rows that pass
the rule above. Before saying "X is not expressed in Z", read the atlas rows
(`/atlas/expression`, all genes x groups, no threshold) and report `pct_expressing`,
`pseudobulk_cp10k` and donor support. Also check that the gene and group exist in that dataset:
a gene missing from the summaries comes back with a warning, not with zeros.

**Ambient RNA in snRNA.** Very highly expressed transcripts (rod genes such as RHO, also
GNAT1, PDE6 and SAG) are detected at low levels in many non-expressing nuclei. A
`pct_expressing` of 0.05-0.3 for a rod gene in Müller glia, amacrine or bipolar nuclei is
usually contamination, not expression. Rule 2 removes most of these edges, but the atlas rows
still show them. Treat such rows as contamination unless the gene is also specific there in an
scRNA atlas or in another tissue, and say so.

## 4. A Route A answer in at most six calls

1. `GET /release`: `kg_release`, atlases and versions, predicates present.
2. `GET /entities/search?q=...`: exact CURIE / symbol match only (synonym or full-text hits need
   checking).
3. `GET /atlas/expression?genes=...&level=majorclass|celltype` (add `dataset=` to stay in one atlas).
4. `GET /relationships?subject=<CURIE>&predicate=...` (or `knowledge_level=`).
5. `GET /evidence/{edge_id}` for the edges you cite.
6. `GET /datasets?entities=...|tissue=...` when the next step is an analysis.

The parameters of the worked questions below:

```python
Q1_GENE = os.environ.get("Q1_GENE", "LRAT")
Q1_DATASET = os.environ.get("Q1_DATASET", "visionkb:ds-hrca-snrna")
Q2_GENE = os.environ.get("Q2_GENE", "RHO")
Q3_GENE = os.environ.get("Q3_GENE", "PRPF31")
```

### 4.0 Which release am I querying?

```python
rel = get("/release")
save("release", rel)
print("kg_release:", rel["kg_release"], "| biolink", rel["data"]["biolink_version"])
print("predicates:", rel["data"].get("predicates_in_graph"))
print(
    "known issues:",
    [(k["id"], k["title"], k["status"]) for k in rel["data"].get("known_issues", [])],
)
for a in rel["data"]["atlases"]:
    print("  atlas", a["dataset_id"], a["atlas_version"])
expect = os.environ.get("VISIONKB_EXPECT_RELEASE")
assert expect is None or rel["kg_release"] == expect, (rel["kg_release"], expect)
```

TBD (pending the run on the real release)

### 4.1 In which classes and cell types is LRAT expressed? (expression, observation)

```python
print(f"\n# Q1 {Q1_GENE}: expression by class and cell type")
gene, hits = resolve(Q1_GENE)
save("q1_search", hits)
show(hits["data"], ["id", "symbol", "name", "match"])

for level in ("majorclass", "celltype"):
    ex = get("/atlas/expression", genes=gene, dataset=Q1_DATASET, level=level, limit=5)
    save(f"q1_atlas_{level}", ex)
    print(f"  atlas {level}: total rows {ex['page']['total']}")
    show(
        ex["data"],
        [
            "group_label",
            "cell_type_id",
            "pct_expressing",
            "pseudobulk_cp10k",
            "n_donors_expressing",
            "n_donors",
        ],
    )

reg = get("/atlas/expression", genes=gene, dataset=Q1_DATASET, level="region_majorclass", limit=5)
save("q1_atlas_region_majorclass", reg)
print(f"  atlas region_majorclass (Parquet only, no KG edges): total rows {reg['page']['total']}")
show(
    reg["data"],
    ["group_label", "region", "pct_expressing", "pseudobulk_cp10k", "n_donors_expressing"],
)

edges = get("/relationships", subject=gene, predicate="biolink:expressed_in", limit=50)
save("q1_expressed_in_edges", edges)
print(f"  expressed_in edges: {edges['page']['total']}")
show(edges["data"][:10], ["edge_id", "knowledge_level"])
for e in edges["data"][:10]:
    print("   ", e["object"]["id"], e["object"]["name"], e["summary"])

if edges["data"]:
    ev = get(f"/evidence/{edges['data'][0]['edge_id']}", limit=10)
    save("q1_evidence_top_edge", ev)
    print(
        "  evidence for", ev["data"]["edge"]["object"]["id"], "study_results:", ev["page"]["total"]
    )
    show(
        ev["data"]["study_results"],
        [
            "dataset_id",
            "atlas_version",
            "level",
            "group_label",
            "pct_expressing",
            "n_donors_expressing",
            "method",
        ],
    )
```

TBD (pending the run on the real release)

### 4.2 Which major class shows the highest RHO? (ranking, ambient RNA)

```python
print(f"\n# Q2 {Q2_GENE}: top major class, then the cell-type edges checked against it")
rho, _ = resolve(Q2_GENE)
top = get("/atlas/expression", genes=rho, level="majorclass", sort="pseudobulk_cp10k", limit=200)
save("q2_atlas_majorclass_all_datasets", top)
by_ds = {}
for r in top["data"]:
    by_ds.setdefault(r["dataset_id"], []).append(r)
for ds, rows in by_ds.items():
    print(f"  {ds} {rows[0]['dataset_version']}: top {rows[0]['group_label']}")
    show(rows[:3], ["group_label", "cell_type_id", "pct_expressing", "pseudobulk_cp10k"])
    detected = [r["group_label"] for r in rows if r["pct_expressing"] >= 0.10]
    print(f"    groups with pct>=0.10: {detected}")

# majorclass first, then the cell-type edges: an edge to a small subtype of ANOTHER class is
# possible contamination (ambient RNA or doublets), not expression
ct = get("/atlas/expression", genes=rho, dataset=Q1_DATASET, level="celltype", limit=200)
save("q2_atlas_celltype", ct)
rows_at = {
    "majorclass": {r["cell_type_id"]: r for r in by_ds[Q1_DATASET]},
    "celltype": {r["cell_type_id"]: r for r in ct["data"]},
}
rho_edges = get("/relationships", subject=rho, predicate="biolink:expressed_in", limit=200)
save("q2_expressed_in_edges", rho_edges)
print(f"  expressed_in edges for {Q2_GENE}: {rho_edges['page']['total']}")
top_class = by_ds[Q1_DATASET][0]["cell_type_id"]  # e.g. CL:0000604 retinal rod cell
for e in rho_edges["data"]:
    o = e["object"]["id"]
    parents = get("/relationships", subject=o, predicate="biolink:subclass_of", limit=10)["data"]
    parent_ids = [x["object"]["id"] for x in parents]
    lvl = "majorclass" if o in rows_at["majorclass"] else "celltype"
    r = rows_at[lvl].get(o, {})
    flag = "" if o == top_class or top_class in parent_ids else "  <- other class: check"
    print(
        f"   {o} {e['object']['name']} parent={parent_ids} {lvl} n_cells={r.get('n_cells')} "
        f"pct={r.get('pct_expressing')} cp10k={r.get('pseudobulk_cp10k')}{flag}"
    )
```

TBD (pending the run on the real release)

### 4.3 Which diseases are associated with PRPF31, with PMIDs? (curated claims)

```python
print(f"\n# Q3 {Q3_GENE}: disease edges (curated claims) and their evidence")
g3, _ = resolve(Q3_GENE)
allrel = get("/relationships", subject=g3, limit=200)
save("q3_all_edges", allrel)
levels = {}
for e in allrel["data"]:
    k = (e["predicate"], e["knowledge_level"], e["primary_knowledge_source"])
    levels[k] = levels.get(k, 0) + 1
for k, n in sorted(levels.items()):
    print("  ", *k, n)
dis = get("/relationships", subject=g3, object_category="biolink:Disease", limit=50)
save("q3_disease_edges", dis)
print(f"  edges to diseases: {dis['page']['total']}")
for e in dis["data"]:
    print(
        "   ",
        e["predicate"],
        e["object"]["id"],
        e["object"]["name"],
        e["knowledge_level"],
        e["agent_type"],
        e["primary_knowledge_source"],
        e["publications"],
    )
if dis["data"]:
    ev3 = get(f"/evidence/{dis['data'][0]['edge_id']}")
    save("q3_evidence", ev3)
    print("  publications:", ev3["data"]["publications"])
    show(ev3["data"]["study_results"], ["id", "pmid", "grade"])
    gs = get("/gene-sets", entity=dis["data"][0]["object"]["id"], kind="disease_genes", limit=20)
    save("q3_gene_set_disease", gs)
    print(f"  genes associated with {dis['data'][0]['object']['id']}: {gs['page']['total']}")
    show(gs["data"], ["gene_id", "symbol", "score"])
```

TBD (pending the run on the real release)

### 4.4 Which atlases can I attach for RPE, or for retina? (datasets, bind records)

```python
print("\n# Q4 datasets with bind records")
rpe = get("/entities/search", q="retinal pigment epithelial cell", category="biolink:Cell", limit=3)
save("q4_search_rpe", rpe)
show(rpe["data"], ["id", "name", "match"])
for label, params in (
    (
        "rpe_cells",
        {
            "entities": next(
                h["id"] for h in rpe["data"] if h["name"] == "retinal pigment epithelial cell"
            )
        },
    ),
    ("tissue_retina", {"tissue": "UBERON:0000966"}),
):
    ds = get("/datasets", limit=20, **params)
    save(f"q4_datasets_{label}", ds)
    print(f"  {label}: {ds['page']['total']} datasets")
    for d in ds["data"]:
        print(
            "   ",
            d["id"],
            d["version"],
            d["assay"],
            d["n_cells"],
            d["access_level"],
            d["matched"],
            d["bind"]["name"],
        )

print("\ndone:", SEQ[0], "responses saved in", OUT)
```

TBD (pending the run on the real release)

## 5. The same with the MCP server

The `visionkb-kg` MCP server (from [aiscientist-mcp](https://github.com/lijinbio/aiscientist-mcp))
wraps the same endpoints, one tool each; arguments are the query parameters above. The tool
names below are the server's; this skill's runs used the HTTP API only.

| MCP tool | HTTP endpoint | Use |
| --- | --- | --- |
| `get_release` | `GET /v1/release` | release id, atlases, counts, predicates |
| `search_entities` | `GET /v1/entities/search` | name, symbol, synonym or CURIE to CURIE |
| `get_relationships` | `GET /v1/relationships` | typed edges from or to an entity |
| `get_evidence` | `GET /v1/evidence/{edge_id}` | StudyResults and publications of one edge |
| `get_gene_set` | `GET /v1/gene-sets` | genes expressed in a cell type, or genes of a disease |
| `query_atlas_expression` | `GET /v1/atlas/expression` | atlas summary rows, no threshold |
| `find_datasets` | `GET /v1/datasets` | registry records with bind records |

## 6. Validate before answering

1. **Release.** Every envelope has the same `kg_release` as `/release`. Mixing releases in one
   answer is an error.
2. **Resolution.** `match` is `exact_id` or `exact_symbol`. A `synonym` or `fulltext` hit must be
   checked by name; HGNC previous symbols and aliases are synonyms here.
3. **Warnings.** Read them: "not found in the expression summaries", "matches N genes",
   deprecated predicates, and lower-than-graph thresholds all arrive as warnings.
4. **Paging.** `page.total` larger than the rows you read means you have not seen everything
   (search returns ranked top-k with `total: null`).
5. **Donor support.** A high `pct_expressing` with `n_donors_expressing` of 0-1 is weak; say so.
6. **Ambient RNA and absence.** As in section 3: no edge does not mean no expression; abundant
   transcripts in snRNA leak into other classes.
7. **Access level.** HECA datasets are `access_level: lab` until published; do not send their rows
   outside the lab.

## 7. Report

- `kg_release`, and for every expression number the `dataset_id` and `dataset_version`;
- each entity with its CURIE and how it was resolved;
- expression (observation) and curated claims (knowledge_assertion) in separate paragraphs, each
  claim with `primary_knowledge_source` and PMIDs;
- for expression: level, group, `pct_expressing`, `pseudobulk_cp10k`, `n_donors_expressing` /
  `n_donors`; the ambient-RNA and absence caveats where they apply;
- for datasets: id, version, assay, cell count, `access_level` and the `bind` record;
- what was not checked (e.g. other atlases, other levels, pages not read).

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| HTTP 401 | missing or wrong bearer token | check `VISIONKB_API_TOKEN_FILE` |
| 400 `missing_anchor` | `/relationships` without `subject` or `object` | anchor on a CURIE |
| 400 `predicate_not_in_release` | predicate not used in this release | read `predicates_in_graph` from `/release` |
| `httpx.InvalidURL: Invalid port: ':1]'` | a `[::1]` entry in `NO_PROXY` (httpx 0.28.1) | remove that entry for the client process |
| 503 on `/v1/ready` | Neo4j, summaries or PostgreSQL down | `bin/visionkb health` on the server |
