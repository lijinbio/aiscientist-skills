---
name: compare-conditions-by-celltype
description: Condition-vs-control differential expression within each cell type (for example KO vs WT, or disease vs control, per cell type) with scanpy rank_genes_groups (Wilcoxon, explicit reference group). Takes an AnnData with a condition column and an existing cell-type column and writes per-cell-type DE tables, a volcano plot per cell type, a summary table, the genes changed in the same direction in two or more cell types, and the de_KEY_all.csv and universe hand-off files that enrichment reads. Use for a stratified condition comparison outside AiScientist, or inside it when the design is one the built-in tool cannot express (a paired or covariate-adjusted comparison, a custom shared-signature rule, a non-standard figure). In AiScientist, run_de with groupby, reference and stratify_by covers the common case.
license: MIT
compatibility: Python 3.12+ with scanpy, anndata and matplotlib (conda or pip). No GPU, no scheduler.
metadata:
  category: single-cell
  version: "1.0.0"
  status: community
  author: "Yijun Sun"
  aliases: "condition_by_celltype"
  tags: "scrna-seq, snrna-seq, differential-expression, scanpy, wilcoxon, cell-type"
  tested-with: "scanpy 1.12.1, anndata 0.12.16, pandas 2.3.3, numpy 2.4.6, matplotlib 3.10.9, Python 3.13.9"
  compute: "1 CPU, under 1 GB RAM (0.3 GB peak), about 2 s for 260 cells x 50 genes"
  requires-gpu: "false"
  scheduler: "none"
  requires-network: "install"
  requires-secrets: "none"
---

# Compare conditions within each cell type

`scripts/reference.py` runs, for each cell type, `sc.tl.rank_genes_groups(..., groups=[CONDITION],
reference=REFERENCE, method="wilcoxon")` on the cells of that type, then collects the changed
genes and looks for a shared cross-cell-type signature: genes changed in the same direction in at
least two cell types. It is the pattern behind a KO-vs-WT or disease-vs-control report.

The most likely mistakes are re-clustering a dataset that already carries cell-type labels
(reuse the existing column) and dropping the hand-off files `tables/de_<CELLTYPE_KEY>_all.csv` and
`tables/de_<CELLTYPE_KEY>_universe.txt`. Enrichment tools discover DE results by exactly those
names. Without them, AiScientist's `run_enrichment` falls back to a single pooled gene list (every
cell type collapsed into one group, the stratification lost) and to a constant 20,000-gene
over-representation background, which inflates every enrichment p-value.

Tested on synthetic data only (`tests/`: 260 cells x 50 genes, log-normalised; Rod, Cone and MG
with 40 KO and 40 WT cells each, a rare type with 10 + 10 cells that must be skipped, two genes
planted up and two down in KO in both Rod and Cone, one up only in MG) with scanpy 1.12.1,
anndata 0.12.16, pandas 2.3.3, numpy 2.4.6, matplotlib 3.10.9 and Python 3.13.9.

## When to use it

In AiScientist, **use the tool first**:

```text
run_de(groupby="<condition column>", reference="<control level>", stratify_by="<cell-type column>")
```

It runs condition-vs-reference within each cell type, writes the tables `run_enrichment` and
`run_gsea_prerank` discover, reports up/down counts per cell type, and lists the cell types it
skipped for too few cells. It needs only QC (`run_scanpy_qc`) first. Use this script when the tool
cannot express the design (a paired or covariate-adjusted comparison, a custom shared-signature
rule, a figure the tool does not draw), or outside AiScientist. It is the same
`rank_genes_groups(reference=...)` loop, written out so you can change it.

## 1. Environment setup

```bash
mamba create -y -n scanpy_1.12 -c conda-forge python=3.13 scanpy=1.12.1 anndata=0.12.16
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate scanpy_1.12
python -c "import scanpy; print(scanpy.__version__)"
```

Inside an AiScientist run, the analysis image already has scanpy.

## 2. Prepare inputs

- An AnnData with log-normalised expression (Wilcoxon fold changes assume log1p data), a
  condition column and an existing cell-type column in `obs`. The script reads
  `$AISCIENTIST_WORK/adata_qc.h5ad` (the QC checkpoint, which keeps the original `obs` labels),
  else the file named by `$AISCIENTIST_DATASET`.
- If the object has `.raw`, scanpy tests `.raw` by default; otherwise `X`.
- `$AISCIENTIST_ARTIFACTS` is where tables and figures go.

Check before running: both columns exist, both condition levels are present, and how many cells
of each level each cell type has (`pd.crosstab(adata.obs[CELLTYPE_KEY], adata.obs[CONDITION_KEY])`).

## 3. Configure

Edit the CONFIG block at the top of the script to columns and levels that exist in `adata.obs`:

| Variable | Meaning | Default |
| --- | --- | --- |
| `CONDITION_KEY` | `obs` column naming the experimental groups | `sampleid` |
| `CONDITION` | the group of interest (case) | `KO` |
| `REFERENCE` | the baseline / control group | `WT` |
| `CELLTYPE_KEY` | existing cell-type column to stratify by (reuse it) | `majorclass` |
| `MIN_CELLS` | skip a cell type with fewer cells than this in either group | `30` |
| `LFC` | \|log2FC\| threshold for "significant" | `1.0` |
| `PADJ` | adjusted-p threshold | `0.05` |

## 4. Run

```bash
export AISCIENTIST_WORK=/path/to/work AISCIENTIST_ARTIFACTS=/path/to/results
export AISCIENTIST_DATASET=/path/to/dataset.h5ad   # only read when work/ has no adata_qc.h5ad
python scripts/reference.py
```

In AiScientist: read the script with `read_skill_reference`, adapt the CONFIG values to this
dataset, and run it with `run_code`, which sets the variables. Afterwards call `run_enrichment`
with **no** `genes` argument, so it picks up `tables/de_<CELLTYPE_KEY>_all.csv` itself and runs
over-representation per cell type and per direction.

Outputs:

| Path | Contents |
| --- | --- |
| `tables/DEG/DEG_<celltype>.csv` | every gene's statistics for that cell type, sorted by adjusted p |
| `figures/DEG/volcano_<celltype>.png` | log2FC against −log10(adjusted p), significant genes highlighted |
| `tables/DEG_summary.csv` | per cell type: cells per group, significant / up / down counts, `skipped` |
| `tables/shared_up_DEGs.csv`, `shared_down_DEGs.csv` | genes significant in the same direction in two or more cell types, most shared first |
| `tables/de_<CELLTYPE_KEY>_all.csv` | hand-off: significant rows of every cell type, both directions, columns `group, gene, log2fc, pval, pval_adj, score` |
| `tables/de_<CELLTYPE_KEY>_universe.txt` | hand-off: every gene tested, one per line (the enrichment background) |

Keep the two hand-off files exactly as named. Their `group` column is the cell type, and both
directions are in them: a rule that keeps only the top of a score-ordered list would silently drop
every down-regulated gene. No DE tool labels this table, so prioritize-disease-genes-with-atlas
reads it only with `de_is_condition_contrast = True`.

## 5. Validate before using the output

1. `per_celltype` in the printed summary: which cell types were tested and which were skipped as
   `too_few_cells` (unused categories of a categorical column also appear there with 0 cells).
2. `DEG_<celltype>.csv`: fold changes of a few units, not tens (tens suggest raw counts in the
   matrix). Housekeeping, mitochondrial or ribosomal genes at the top of every cell type suggest a
   quality difference between the conditions rather than biology.
3. The shared signature: a gene shared across many cell types is either a real global response
   or an ambient-RNA or batch effect; check whether it is a highly expressed marker of one
   abundant cell type.
4. The hand-off files exist and the table holds both signs of `log2fc`.

## Report

The comparison (condition column, case, reference), the cell-type column, the thresholds, per
cell type the cell counts and up/down numbers, the skipped cell types, and the shared up and down
genes. Cells are not independent replicates: with several samples per condition, say so, treat
the Wilcoxon p-values as an exploratory ranking, and prefer a pseudobulk test per sample.
