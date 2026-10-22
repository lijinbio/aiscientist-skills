---
name: crossvalidate-scgpt-vs-leiden
description: Cross-validate scGPT per-cell cell-type predictions against the data's own structure. Joins the scGPT predictions CSV to a clustered AnnData by barcode, never by row position (scGPT labels every raw cell, QC keeps a subset), and for the Leiden clusters and any existing majorclass or celltype labels writes a reference-by-scGPT confusion table, each group's top scGPT label and purity, an exact-string agreement and the scGPT confidence distribution, as CSV and JSON. Use after scGPT label transfer (for example AiScientist's scgpt_annotate) to judge which predicted labels the data supports, to compare scGPT labels with labels the dataset already carries, or when merging predictions onto an AnnData fails with a length or alignment error.
license: MIT
compatibility: Python 3.12+ with scanpy, anndata and pandas (conda or pip). No GPU, no scheduler; the scGPT run that makes the predictions is separate.
metadata:
  category: single-cell
  version: "1.0.0"
  status: community
  author: "Yijun Sun"
  aliases: "crossvalidate_scgpt_vs_leiden"
  tags: "scrna-seq, snrna-seq, cell-type-annotation, scgpt, clustering, validation"
  tested-with: "scanpy 1.12.1, anndata 0.12.16, pandas 2.3.3, numpy 2.4.6, Python 3.13.9"
  compute: "1 CPU, under 1 GB RAM (0.3 GB peak), seconds for 100 predicted and 85 clustered cells"
  requires-gpu: "false"
  scheduler: "none"
  requires-network: "install"
  requires-secrets: "none"
---

# Cross-validate scGPT labels against clusters

`scripts/reference.py` lines up scGPT's per-cell predictions with a clustered AnnData and asks,
for each reference column available, how the scGPT labels distribute within each group: the
independent Leiden clusters (data-driven structure) and any existing `majorclass` / `celltype`
labels the data already carries, which make it a true cross-validation. It writes one confusion
table per reference column, a per-group purity summary, and the scGPT confidence distribution.

The most likely mistake is a positional join. scGPT labels **every** cell of the raw query, while
QC and Leiden run on a filtered subset, so the two cell sets differ. Align by barcode. A
positional merge, or assigning a length-N prediction column onto an M-cell AnnData, raises a
pandas alignment error and the step fails; this is the most common way these runs stall. If the
barcodes do not match at all (a suffix such as `-1` on one side only), the script stops instead of
guessing.

Tested on synthetic data only (`tests/`: 100 predicted cells in shuffled order, 80 of them kept
after QC in a different order plus 5 cells scGPT never saw, 5 cones planted as "Rod") with
scanpy 1.12.1, anndata 0.12.16, pandas 2.3.3, numpy 2.4.6 and Python 3.13.9. The tests check the
barcode join, the cell counts on each side, the planted purity and the clear error when no
barcode is shared.

## 1. Environment setup

```bash
mamba create -y -n scanpy_1.12 -c conda-forge python=3.13 scanpy=1.12.1 anndata=0.12.16
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate scanpy_1.12
python -c "import scanpy; print(scanpy.__version__)"
```

Inside an AiScientist run, the analysis image already has scanpy. No curated AiScientist tool
covers this step.

## 2. Prepare inputs

- `$AISCIENTIST_ARTIFACTS/data/scgpt_predictions.csv`: one row per cell. The barcode column is the
  first of `cell`, `barcode`, `index` present, else the first column; the label column is
  `predictions`, else `prediction`; the confidence column is the first of `confidence`, `score`,
  `prob` present (optional). AiScientist's `scgpt_annotate` writes it there with columns
  `barcode, predictions, confidence`.
- `$AISCIENTIST_WORK/adata_clustered.h5ad`: the clustered checkpoint, with `obs["leiden"]` and,
  where the data has them, the original `majorclass` / `celltype` labels. Its `obs_names` must be
  the same barcodes as the CSV.

Check before running: a few barcodes from each side, side by side. Fix a systematic difference
(suffix, prefix, sample tag) in a copy of the CSV, not by position.

## 3. Configure

The script needs no edits when the inputs follow the layout above. Adapt it when they do not:

| What | Where in the script | Default |
| --- | --- | --- |
| predictions file | `pred = pd.read_csv(...)` | `$AISCIENTIST_ARTIFACTS/data/scgpt_predictions.csv` |
| barcode, label and confidence columns | `bc_col`, `label_col`, `conf_col` | detected as above |
| clustered object | `adata = sc.read_h5ad(...)` | `$AISCIENTIST_WORK/adata_clustered.h5ad` |
| reference columns | `ref_cols` | those of `leiden`, `majorclass`, `celltype` present |
| low-confidence cut-off | `low_conf_frac(<0.5)` | `0.5` |

## 4. Run

```bash
export AISCIENTIST_WORK=/path/to/work AISCIENTIST_ARTIFACTS=/path/to/results
python scripts/reference.py
```

In AiScientist: read the script with `read_skill_reference`, adapt the column names if the CSV
differs, and run it with `run_code`, which sets both variables.

Outputs:

| Path | Contents |
| --- | --- |
| `tables/scgpt_vs_<ref>_confusion.csv` | cells per reference group (rows) and scGPT label (columns), one per reference column |
| `tables/scgpt_crossvalidation.json` | cells compared, cells only in the CSV (QC-filtered), cells without a prediction; per reference column the group count, exact-string agreement and per group the top scGPT label, purity and size; confidence mean, median and fraction below 0.5 |

## 5. Validate before using the output

1. `cells_compared` against the size of the clustered object. Most clustered cells should have a
   prediction; a large `cells_in_adata_without_a_prediction` means the barcodes only partly
   match.
2. `cells_scgpt_only(qc_filtered_out)`: the cells QC removed. Their labels are not part of the
   comparison.
3. Per group `purity` and `top_scgpt_label`: a Leiden cluster with high purity supports that
   label; a cluster split between several labels is either a mixed cluster or a label scGPT
   cannot separate. Read the confusion table, not only the top label.
4. `exact_string_agreement` is **rough**. scGPT's reference taxonomy may name a class differently
   from the data's own labels ("Rod" against "rod photoreceptor"), and Leiden cluster ids never
   equal label strings, so read the confusion table and purity rather than this number.
5. `confidence`: a high `low_conf_frac(<0.5)` means many calls are weak; check whether the
   low-confidence cells concentrate in particular clusters.

## Report

The predictions file and the clustered object, the cell counts (compared, QC-filtered,
without a prediction), per reference column each group's top scGPT label and purity, the groups
where scGPT disagrees with the existing labels, and the confidence summary. Say which scGPT
labels the data supports and which it does not; do not report the exact-string agreement as an
accuracy.
