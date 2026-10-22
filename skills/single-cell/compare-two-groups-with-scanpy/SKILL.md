---
name: compare-two-groups-with-scanpy
description: Differential expression between two named groups of cells (for example disease vs control, or cluster 3 vs cluster 5) with scanpy rank_genes_groups (Wilcoxon) and an explicit reference group, from an AnnData file to a ranked CSV table and a JSON summary. Use when a question compares exactly two groups that a per-cluster one-vs-rest test does not answer, or when choosing the group column, the two groups and the significance thresholds for such a comparison.
license: MIT
compatibility: Python 3.12+ with scanpy and anndata (conda or pip). No GPU, no scheduler.
metadata:
  category: single-cell
  version: "1.0.0"
  status: community
  author: "Yijun Sun"
  aliases: "pairwise_de"
  tags: "scrna-seq, snrna-seq, differential-expression, scanpy, wilcoxon"
  tested-with: "scanpy 1.12.1, anndata 0.12.16, pandas 2.3.3, numpy 2.4.6, Python 3.13.9"
  compute: "1 CPU, under 1 GB RAM, seconds for 120 cells x 40 genes"
  requires-gpu: "false"
  scheduler: "none"
  requires-network: "install"
  requires-secrets: "none"
---

# Compare two groups of cells with scanpy

`scripts/reference.py` compares two groups of one `obs` column with
`sc.tl.rank_genes_groups(..., groups=[A], reference=B, method="wilcoxon")`. It reads an AnnData
checkpoint, writes every gene's statistics to a CSV table, and prints a JSON summary. The most
likely mistake is comparing raw counts: the Wilcoxon fold changes assume log-normalized `X`.

Tested on synthetic data only (`tests/`: 120 cells, 40 genes, 5 planted up-regulated genes) with
scanpy 1.12.1, anndata 0.12.16, pandas 2.3.3, numpy 2.4.6 and Python 3.13.9. It has been the
AiScientist template for A-vs-B comparisons since July 2026.

## 1. Environment setup

```bash
mamba create -y -n scanpy_1.12 -c conda-forge python=3.13 scanpy=1.12.1 anndata=0.12.16
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate scanpy_1.12
python -c "import scanpy; print(scanpy.__version__)"
```

Inside an AiScientist run, the analysis image already has scanpy.

## 2. Prepare inputs

- An AnnData file with log-normalized expression in `X` and the group labels in an `obs`
  column. The script reads `adata_clustered.h5ad` from `$AISCIENTIST_WORK`, else
  `adata_qc.h5ad`.
- `$AISCIENTIST_ARTIFACTS` is where the table goes (`tables/` is created).

Check before running: the column exists, both groups are present, and each has enough cells
(a group of a handful of cells gives unstable p-values).

## 3. Configure

Edit the three values at the top of the script:

| Variable | Meaning | Example |
| --- | --- | --- |
| `GROUP_KEY` | the `obs` column holding the groups | `condition`, `leiden` |
| `GROUP_A` | the group of interest | `disease` |
| `GROUP_B` | the reference group | `control` |

A gene counts as significant at adjusted p < 0.05 and |log fold change| > 1. Change the two
thresholds in the `sig = ...` line only with a reason.

## 4. Run

```bash
export AISCIENTIST_WORK=/path/to/work AISCIENTIST_ARTIFACTS=/path/to/results
python scripts/reference.py
```

In AiScientist: read the file with `read_skill_reference`, set the three values for this dataset,
and run it with `run_code`, which sets both variables.

## 5. Validate before using the output

1. `n_cells` in the summary: both groups present, neither tiny.
2. `tables/de_<A>_vs_<B>.csv`: sorted by `pvals_adj`; fold changes of a few units, not tens
   (tens suggest raw counts in `X`).
3. `top_up` / `top_down`: known markers of either group should appear when the groups are cell
   types; housekeeping or mitochondrial genes at the top suggest a quality difference between the
   groups rather than biology.

## Report

The comparison (column, A, B), the cell count of each group, the number of significant genes with
the thresholds used, the top genes in each direction, and the table path. Cells are not
independent replicates: for a condition comparison with several samples, say so, and prefer a
pseudobulk test per sample.
