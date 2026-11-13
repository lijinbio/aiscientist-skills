---
name: analyze-scrna-with-mcp
description: Run QC, clustering, differential expression, enrichment and marker annotation through an already configured scrna-analysis MCP service. Use for an AnnData workflow when this service is available and its checkpoints and asynchronous task results must be carried between steps; retain the existing standalone workflow when it is not registered.
license: MIT
metadata:
  category: single-cell
  version: 0.1.0
  status: community
  tags: mcp, scrna-analysis
  tested-with: aiscientist-mcp-scrna-analysis 0.0.3, common 0.0.4, MCP 2.3.0, scanpy 1.12.5; 11 tools compared with original code on real HECA counts
  compute: 4 CPUs, 48 GB requested; 480 real cells x 1550 genes, 6 samples, 2 tissue regions; this is a regression subset, not full-atlas sizing
  requires-gpu: 'false'
  scheduler: optional
  requires-network: install
  requires-secrets: none
  mcp-server: scrna-analysis
  mcp-package-version: 0.0.3
  image: "docker://ghcr.io/liujs123456/mcp-scrna-analysis@sha256:945b05f973fee2aaa273461bedd2fe64948a1f0cc2ebe569c6c145106d71c92c"
  cpus: "4"
  mem_gb: "48"
  time_limit: "01:00:00"
---

# Analyze single-cell data with the scRNA MCP service

Use the registered `scrna-analysis` service to execute analysis, preserving one `analysis_id`
through a dependent chain. This skill contains no replacement scientific implementation.

## Select an available execution path

Read the client's actual tool inventory and advertised schemas. Tool names below are the
server's native names; a host may qualify them. Do not invent a `mcp_` prefix or call an
unregistered name. If this service is absent, keep the currently available AiScientist tools
or the installed standalone analysis skill. This migration skill does not change their image,
install an unpublished release, or retire the legacy path. Its image pin names the published fork validation release.

The service operator binds `SCRNA_DATASET`, `SCRNA_READ_ROOTS`, and writable `AISCI_DATA_DIR`.
An explicit `dataset` must be admitted on the server host. Tool `input` selects a checkpoint
inside this analysis's `work/` or `artifacts/`; it is not a general filesystem reader.

## Choose the calculation

| Tool | Use and important parameters |
| --- | --- |
| `run_scanpy_qc` | An AnnData input: inspect mitochondrial gene matching and set `min_genes`, `min_cells`, `max_pct_mt`, `n_top_genes` for the assay. |
| `run_doublet_detection` | An explicit additional doublet step only when upstream QC has not already removed doublets. |
| `run_integration` | Specify a real `batch_key` and supported `method`; do not use biological condition as a technical batch without justification. |
| `run_clustering` | Set `n_pcs`, `n_neighbors`, `resolution`; inspect actual cluster sizes and embedding. |
| `run_de` | Inspect `groupby` and the advertised contrast parameters; retain tested group/reference and cell-count provenance. |
| `run_depth_matched_de` | A depth-matched sensitivity analysis with explicit `groupby`, `reference`, and optional `stratify_by`; not a substitute for independent replicates. |
| `run_enrichment` | Enrich DE tables against operator-staged GMT `gene_sets`; preserve the background and tested gene counts. |
| `run_gsea_prerank` | Analyze ranked gene lists; report ties, set coverage, permutations, and configured gene-set sources. |
| `run_pseudobulk_de` | Replicate-aware counts using `sample_key`, `condition_key`, and optional `group_key`; never treat individual cells as biological replicates. |
| `run_composition` | Compare group proportions by real sample and condition; retain low-count and replication caveats. |
| `run_marker_annotation` | Apply curated `reference` or explicit `panel`, `discriminators`, and `cluster_key`. The reference infers species from genes; there is no `species` argument. |

Follow the checkpoint dependencies exposed by the tools. QC normally precedes clustering,
then DE and marker annotation. Enrichment consumes prior DE/rank tables. Do not interpret a
QC result with zero mitochondrial matches as evidence that high-mitochondrial cells were removed.

## Complete each task and carry outputs

Save the returned `analysis_id` and `task_id`. With Slurm/local execution, poll
`scrna_job_status(analysis_id, task_id)` until `COMPLETED`; retain a returned Slurm `job_id`.
A failure is a failed analysis, even if partial files exist. Inline calls already wait inside
the caller's allocation. Do not submit two writers to one analysis concurrently.

Use `artifact_root` for downloadable artifacts and `checkpoint_path` for the actual AnnData.
These are server-side paths: the application must explicitly collect them. An operator can
bind `SCRNA_CHECKPOINT_ROOT` for a CellQC handoff. Imported upstream checkpoints are tracked;
if CellQC later changes one, use a new `analysis_id` when the server refuses the old chain.
Never combine old clustering with replacement QC. `rerun=true` forces another attempt with
unchanged inputs; it is not permission to bypass the upstream-change check.

## Validate and report

Check cell/gene retention, counts-layer provenance, batch and sample identities, group sizes,
full DE tables, multiple-testing columns, and marker concordance. Preserve warnings and
non-estimable groups. Report thresholds, seeds, references, versions, task IDs and collected
artifacts. A table preview is not the complete result.

The native service's 11 tools were compared with the original application calculations on a
public HECA subset: 480 observed cells, 6 samples, fovea/periphery, Rod/BC, 1,550 selected genes.
Original structured results matched after normalizing workspace paths; CSV values matched at
relative tolerance 1e-6 and absolute tolerance 1e-8. This verifies migration parity on that
subset, not the validity of every biological contrast or full-atlas resource requirements.
