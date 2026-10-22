---
name: annotate-clusters-by-markers
description: Reference-free cell-type annotation of clusters from a curated marker panel with scanpy. Signature scores (score_genes) give a z-scored first pass, and the final label is decided on raw log-normalised expression of a few lineage-specific discriminator genes, so lineages that share markers are not mislabelled and clusters with no coherent signal stay Unassigned. Takes a clustered AnnData and writes per-cluster labels with the first-pass call, any correction and its evidence (JSON), a score matrix, a composition table and an annotated h5ad. Use when labelling clusters by markers instead of transferring labels from a reference atlas, when building a marker panel and discriminator table for a tissue, or when a score argmax gives suspicious labels. In AiScientist the built-in run_marker_annotation tool runs this procedure; use the script to change the procedure itself.
license: MIT
compatibility: Python 3.12+ with scanpy and anndata (conda or pip). No GPU, no scheduler.
metadata:
  category: single-cell
  version: "1.0.0"
  status: community
  author: "Yijun Sun"
  aliases: "annotate_clusters_by_markers_v2, annotate_clusters_by_markers"
  tags: "scrna-seq, snrna-seq, cell-type-annotation, marker-genes, scanpy, retina"
  tested-with: "scanpy 1.12.1, anndata 0.12.16, pandas 2.3.3, numpy 2.4.6, Python 3.13.9"
  compute: "1 CPU, under 1 GB RAM (0.3 GB peak), about 2 s for 240 cells x 181 genes"
  requires-gpu: "false"
  scheduler: "none"
  requires-network: "install"
  requires-secrets: "none"
---

# Annotate clusters by marker genes

`scripts/reference.py` labels each cluster of a clustered AnnData from a curated marker panel in
three steps:

1. score every cell against each lineage's panel with `sc.tl.score_genes` (background-corrected
   mean), averaged per cluster;
2. z-score each lineage across clusters and take the argmax, as a **first pass only**;
3. decide the label on **raw** log-normalised expression of 2–4 lineage-specific discriminator
   genes, and assign it only when that lineage's own discriminators are the dominant raw signal.

The most likely mistake is trusting the first pass. Per-lineage z-scoring inflates weak and
ambient signal into confident-looking maxima, so lineages that share markers (RHO/PDE6A across
rod and cone, SLC1A3 across Müller glia and astrocyte) get mislabelled by the argmax alone. The
second most likely mistake is the panel itself: the labels are only as good as the panel, and the
bundled one is **human retina**.

Tested on synthetic data only (`tests/`: six clusters of 40 cells, 181 genes; rod, cone, Müller
glia with a weak reactive GFAP/S100B signal that the z-scored first pass calls astrocyte,
microglia that also express Müller-panel genes, a cluster with no coherent signal, and pericytes)
with scanpy 1.12.1, anndata 0.12.16, pandas 2.3.3, numpy 2.4.6 and Python 3.13.9. The tests check
that the raw check overrules the astrocyte call and records it as a correction, that the noise
cluster stays `Unassigned`, and that markers are found in `.raw` when `X` holds only variable
genes. It supersedes AiScientist's v1 template (`annotate_clusters_by_markers`).

## Why not count marker genes among the top DE genes

The v1 procedure counted how many of a cluster's top-25 DE genes appeared in each marker list and
took the argmax. Both of its flaws produce confident wrong labels rather than visible failures:

- **A set intersection throws away expression.** A gene either is or isn't in the top 25, so a
  lineage with 3 weakly detected markers beats one with 2 strongly expressed ones.
- **It cannot handle shared markers.** `LAMP3` is in both the AT2 and dendritic-cell panels;
  `PDPN` is in both AT1 and lymphatic endothelium. Whichever list overlaps by one more gene wins,
  and nothing in the procedure can notice the ambiguity.

## The rule that decides the label

Signature scores alone will mislabel shared-marker lineages, so the final label comes from raw
expression of a few discriminators. Two consequences are part of the rule, not optional
refinements:

- A cluster whose first-pass call and raw check disagree is **reported as a correction**, with
  both calls kept in the output. That disagreement is evidence about the data; keeping only the
  winner destroys it.
- A cluster with no coherent dominant signal is **`Unassigned`**: likely low quality or a
  doublet. Do not force a label onto it.

A cluster is labelled only if its best lineage's discriminator mean is at least
`MIN_DISCRIMINATOR_MEAN` **and** at least `DOMINANCE_RATIO` times the runner-up lineage's. A
winner that barely edges out the runner-up is exactly the shared-marker case. Confidence is
`high` when the winning mean is at least twice the floor, `medium` otherwise, `none` for
`Unassigned`.

## When to use it

Marker-based (manual) annotation of a clustered object. For label transfer against an annotated
reference atlas, use a reference-based method (such as scGPT) instead.

**Annotate per tissue, not across tissues.** Tissue of origin is the dominant axis of variation,
so one global clustering of a multi-tissue object separates by tissue and washes out
intra-tissue subtypes, and each tissue needs its own panel. Split first, run per tissue.

**Choose the clustering resolution first.** Labels inherit whatever partition they are given, so
a default resolution is an unexamined assumption in every downstream label. Sweep candidate
resolutions, measure bootstrap stability (mean ARI over resampled re-clusterings), and take the
finest resolution that still reproduces; then check that it separates the panel's major lineages.
In AiScientist, `run_clustering` with `select_resolution: true` does this, writes
`tables/resolution_sweep.csv` and reports `resolution_source`; quote it.

## 1. Environment setup

```bash
mamba create -y -n scanpy_1.12 -c conda-forge python=3.13 scanpy=1.12.1 anndata=0.12.16
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate scanpy_1.12
python -c "import scanpy; print(scanpy.__version__)"
```

Inside an AiScientist run, the analysis image already has scanpy.

## 2. Prepare inputs

- `$AISCIENTIST_WORK/adata_de.h5ad`: a clustered AnnData with the cluster labels in an `obs`
  column (`leiden` by default) and log-normalised expression. The file name is the checkpoint
  AiScientist's DE step writes; standalone, save your clustered object under that name. Its
  `rank_genes_groups` results are not used.
- If `.raw` is present, the script scores and checks markers there (the full log-normalised
  matrix, set before subsetting to highly variable genes), so every panel gene is visible, not
  only the genes clustering ran on. Without `.raw` it uses `X`; make sure `X` then holds all
  genes, log-normalised.
- `$AISCIENTIST_ARTIFACTS` is where the tables go (`tables/` is created).

Gene symbols must match the object's namespace and case: the bundled panel is human
(`RHO`, `GLUL`); a mouse object needs `Rho`, `Glul`. Panel genes absent from the object are
dropped and listed, and a lineage with no detected marker cannot be called at all.

## 3. Configure

Edit the CONFIG block at the top of the script:

| Variable | Meaning | Default |
| --- | --- | --- |
| `CLUSTER_KEY` | the `obs` column with the clusters | `leiden` |
| `MIN_DISCRIMINATOR_MEAN` | absolute floor for the winning lineage's discriminator mean | `0.20` |
| `DOMINANCE_RATIO` | how many times the runner-up the winner must reach | `1.5` |
| `PANEL` | lineage to full marker list, used for signature scoring; keys are the labels | human retina, 13 lineages |
| `DISCRIMINATORS` | lineage to the 2–4 specific genes that settle a contested cluster | human retina |

Both thresholds are deliberately visible knobs. On a shallow snRNA-seq object the absolute floor
has to come down, and loosening it is a decision to state in the report.

**Replace `PANEL` and `DISCRIMINATORS` with your tissue's markers.** Search the literature for
the canonical markers of the tissue in hand rather than reusing a panel from another tissue or
writing one from memory, and record where the panel came from.

**Building the discriminator table.** For every lineage in `PANEL`, `DISCRIMINATORS` needs the
genes specific enough to settle a contested cluster, not the whole panel. The useful pattern is
"gene X is in two panels, gene Y is in only one": drop X, keep Y. A gene that appears in two
panels cannot discriminate between them, so it stays in `PANEL` for scoring but leaves
`DISCRIMINATORS`. The bundled retina table:

| Lineage | Confirm with (dominant raw signal) | False positive it overrides |
| --- | --- | --- |
| Rod photoreceptor | RHO / NRL / GNAT1 | cone (shared phototransduction genes) |
| Cone photoreceptor | ARR3 / PDE6H / GNAT2 | rod |
| Muller glia | RLBP1 / GLUL | astrocyte (shared SLC1A3) |
| Retinal astrocyte | GFAP / PAX2 | Muller glia |
| Microglia | C1QA / P2RY12 / CX3CR1 | infiltrating macrophage |
| Vascular endothelium | PECAM1 / VWF / CLDN5 | — |
| Lymphatic endothelium | PROX1 / CCL21 (PECAM1 also present) | vascular endothelium |

Replace the whole table for a different tissue: the shape transfers, not the genes.

## 4. Run

```bash
export AISCIENTIST_WORK=/path/to/work AISCIENTIST_ARTIFACTS=/path/to/results
python scripts/reference.py
```

In AiScientist: prefer the `run_marker_annotation` tool, which implements this procedure and
takes `panel` and `discriminators`, so the panel is the only thing to get right. Use the script
only to change the procedure (a different first pass, an extra confirmation step): read it with
`read_skill_reference`, replace `PANEL` and `DISCRIMINATORS`, and run it with `run_code`, which
sets both variables.

Outputs:

| Path | Contents |
| --- | --- |
| `tables/cluster_cell_types.json` | per cluster: final label, first-pass label, whether the raw check corrected it, discriminator mean, runner-up and its mean, confidence, evidence; plus untestable lineages, absent panel genes, corrected and unassigned clusters, thresholds |
| `tables/celltype_scores_by_cluster.csv` | the raw (un-z-scored) signature score matrix, cluster by lineage |
| `tables/celltype_composition.csv` | cells and percentage per final label |
| `$AISCIENTIST_WORK/adata_annotated.h5ad` | `obs["cell_type"]` and `obs["cluster_note"]` (the evidence string) |

`/` in score column names (`score_Pericyte/SMC`) is replaced by `_` before writing, because h5py
rejects it.

## 5. Validate before using the output

1. `lineages_not_testable` and `panel_genes_absent_from_object` in the printed summary: a
   lineage with no detected marker could not have been called. Many absent genes usually mean a
   species or case mismatch (`RHO` against a mouse object).
2. `corrected_by_raw_check`: read each correction's `first_pass_label`, `runner_up` and
   `evidence`. A correction is expected for shared-marker lineages; many corrections suggest the
   panel's scoring genes are not specific.
3. `unassigned`: check each cluster's size and its top DE genes. A large `Unassigned` cluster can
   be a lineage missing from the panel, not only low-quality cells or doublets.
4. `confidence: medium` labels sit close to the floor; check their discriminator means against
   the other clusters in `celltype_scores_by_cluster.csv`.
5. Known biology: the labels should account for the major cell types expected in the tissue, in
   plausible proportions (`celltype_composition.csv`).

## Report

State the panel and its source, the clustering resolution and how it was chosen, the two
thresholds (and why, if changed), every cluster the raw check corrected (first-pass and final
label), and every cluster left `Unassigned` with its size. An annotation whose corrections and
unassigned clusters are not stated cannot be reviewed.
