---
name: score-gene-signatures-with-scanpy
description: Score every cell for one or more gene signatures with scanpy score_genes (the signature's mean expression minus that of a matched random control gene set) and summarise each score per group, for example cell type by condition, as n, mean, median and IQR, with per-cell scores, box plots and a JSON coverage report. It looks genes up in the matrix actually scored (.raw when present), matches symbols case-insensitively and reports every remap, does not score a signature below a coverage threshold, and refuses integer counts. Use when a per-cell programme score is the deliverable, when the programme is in no gene-set library, or when choosing and checking signature genes for a scoring. To test whether a curated pathway shifts between conditions within a cell type, preranked GSEA on the full contrast ranking (AiScientist run_gsea_prerank) is the better tool.
license: MIT
compatibility: Python 3.12+ with scanpy, anndata and matplotlib (conda or pip). No GPU, no scheduler.
metadata:
  category: single-cell
  version: "1.0.0"
  status: community
  author: "Yijun Sun"
  aliases: "score_signature"
  tags: "scrna-seq, snrna-seq, gene-signature, module-score, scanpy"
  tested-with: "scanpy 1.12.1, anndata 0.12.16, pandas 2.3.3, numpy 2.4.6, matplotlib 3.10.9, Python 3.13.9"
  compute: "1 CPU, under 1 GB RAM (0.3 GB peak), about 2 s for 120 cells x 200 genes"
  requires-gpu: "false"
  scheduler: "none"
  requires-network: "install"
  requires-secrets: "none"
---

# Score gene signatures with scanpy

`scripts/reference.py` scores every cell for each signature with `sc.tl.score_genes`: per cell,
the mean expression of the signature genes minus the mean of a random **control** set drawn from
genes of matched average expression (genes are binned by mean expression, and for each signature
gene `ctrl_size` controls are sampled from its bin). A positive score means the cell expresses
the signature above what its general expression level predicts. It then summarises each score
per group as a distribution (n, mean, median, quartiles), not one number.

The most likely mistake is mixing directions. Score one coherent programme per signature: genes
expected to move in **opposite** directions (a splicing programme and photoreceptor
outer-segment genes, say) belong in separate signatures. Averaged together they cancel, and the
score means nothing.

Three more errors each silently produced a wrong score before the script guarded them:

- **The wrong matrix for the gene lookup.** A clustering checkpoint keeps only the ~2,000 highly
  variable genes in `X`, so a lookup against `X` reported most signature genes as missing although
  they were in the data. The lookup uses the matrix `score_genes` scores: `.raw` (all genes,
  log-normalised) when present.
- **Case.** Symbols match case-insensitively, so a signature written `GFAP` finds `Gfap` on a mouse
  matrix, and every remap is reported. A different **name** is not fixed by case: the human-only
  or yeast name of a gene (`PRP22` for `Dhx8`) stays missing and is listed. A symbol matching
  several genes by case is listed as ambiguous and not used.
- **Low coverage.** A signature with fewer than `MIN_COVERAGE` of its genes found is not scored: a
  score built from two of fifteen genes is a different signature with the original's name on it.

It also refuses integer counts: `score_genes` on raw counts is a depth score, not a programme
score (the deeper cell wins).

Tested on synthetic data only (`tests/`: 120 cells, 50 "variable" genes in `X` and 200 in `.raw`,
a 5-gene signature in mouse case planted in half the cells) with scanpy 1.12.1, anndata 0.12.16,
pandas 2.3.3, numpy 2.4.6, matplotlib 3.10.9 and Python 3.13.9. The tests check the `.raw`
lookup, the case remap, the planted group difference, the coverage refusal and the counts
refusal.

## When to use it

For a per-cell score of a programme no gene-set library holds, or when the per-cell score itself
is the deliverable (to plot on a UMAP, or to compare across cell types and conditions). No
curated AiScientist tool covers per-cell signature scoring.

Not for asking whether a pathway shifts between conditions within a cell type: preranked GSEA
over the contrast's full ranking (AiScientist: `run_gsea_prerank`) already tests the curated gene
sets, spliceosome and mRNA-splicing sets included.

## 1. Environment setup

```bash
mamba create -y -n scanpy_1.12 -c conda-forge python=3.13 scanpy=1.12.1 anndata=0.12.16
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate scanpy_1.12
python -c "import scanpy; print(scanpy.__version__)"
```

Inside an AiScientist run, the analysis image already has scanpy.

## 2. Prepare inputs

- A log-normalised AnnData with the grouping columns in `obs`. The script reads
  `$AISCIENTIST_WORK/adata_clustered.h5ad`, else `adata_qc.h5ad`. If `.raw` is present, it is
  scored (scanpy's default); otherwise `X`, which must then hold all genes.
- `$AISCIENTIST_ARTIFACTS` is where tables and figures go.

The integer-counts check looks at up to 500 cells and refuses a matrix whose values are all whole
numbers with a maximum above 50. Very shallow counts (maximum 50 or below) pass it, so confirm
the matrix is log-normalised yourself.

## 3. Configure

Edit the CONFIG block in the script:

| Variable | Meaning | Default |
| --- | --- | --- |
| `SIGNATURES` | `{name: [gene symbols]}`, one coherent programme per entry; case does not matter | `interferon_response`: IFNG, STAT1, GBP1, CXCL10, IRF1 |
| `GROUP_KEYS` | `obs` columns to summarise over, e.g. `["majorclass", "sampleid"]` for cell type x condition | `["leiden"]` if present, else none |
| `MIN_COVERAGE` | fraction of a signature's genes that must be found to score it | `0.5` |
| `CTRL_SIZE` | control genes per signature gene (scanpy's default) | `50` |
| `SEED` | random state of the control-gene draw | `0` |

Write signature symbols for the species of the data where they differ by more than case, and take
the gene lists from a stated source (a paper, a curated set), not from memory.

## 4. Run

```bash
export AISCIENTIST_WORK=/path/to/work AISCIENTIST_ARTIFACTS=/path/to/results
python scripts/reference.py
```

In AiScientist: read the script with `read_skill_reference`, set `SIGNATURES` and `GROUP_KEYS`
for this dataset, and run it with `run_code`, which sets both variables.

Outputs:

| Path | Contents |
| --- | --- |
| `tables/signature_summary.json` | checkpoint and matrix used, group keys, per signature: genes requested, used, remapped by case, missing, ambiguous, coverage, status; cell count |
| `tables/signature_score_by_group.csv` | per group and signature: n cells, mean, median, q25, q75 |
| `tables/signature_scores_per_cell.csv` | group columns and every score, per cell |
| `figures/signature_<name>_by_group.png` | box plot of the score per group |
| `$AISCIENTIST_WORK/adata_scored.h5ad` | the object with `obs["score_<name>"]` |

If no signature reaches `MIN_COVERAGE`, the script prints the coverage report and stops.

## 5. Validate before using the output

1. `status` and `coverage` per signature in `signature_summary.json`: which signatures were not
   scored, and why.
2. `remapped_by_case`, `missing`, `ambiguous`: a long missing list usually means the symbols
   belong to another species or namespace. A remapped human symbol on a mouse matrix assumes
   name-based orthology; say so.
3. `matrix`: `.raw (all genes, log-normalised)` or `X`. With `X`, check that it was not
   subset to variable genes.
4. `signature_score_by_group.csv`: compare medians and quartiles, not only means; a group of a
   handful of cells gives unstable numbers.
5. A score is relative to the control genes and the dataset: compare it across groups within one
   object, not as an absolute level across datasets.

## Report

Each signature with its gene source, the genes used, remapped and missing, the coverage, the
matrix scored, the grouping, and the per-group medians and quartiles. Cells are not independent
replicates: for a condition comparison with several samples, summarise per sample before testing
a difference.
