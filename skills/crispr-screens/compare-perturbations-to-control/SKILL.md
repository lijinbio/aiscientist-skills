---
name: compare-perturbations-to-control
description: Per-perturbation differential expression against one shared non-targeting control in a pooled CRISPR screen with single-cell readout (Perturb-seq, CROP-seq, CRISPRi or CRISPRa) with scanpy rank_genes_groups (Wilcoxon, explicit reference), from an AnnData with a guide or perturbation column to one DE table per perturbation, a summary table with a target self-knockdown positive control, and the genes shared across perturbations. Use when every guide or target gene must be compared with the same control cells (the AiScientist run_de tool does per-cluster one-vs-rest and does not do this), when collapsing guides to target genes, or when checking which guides lowered their own target.
license: MIT
compatibility: Python 3.12+ with scanpy and anndata (conda or pip). No GPU, no scheduler.
metadata:
  category: crispr-screens
  version: "1.0.0"
  status: community
  author: "Yijun Sun"
  aliases: "perturbation_de_vs_control"
  tags: "crispr, perturb-seq, crop-seq, scrna-seq, differential-expression, scanpy, wilcoxon"
  tested-with: "scanpy 1.12.1, anndata 0.12.16, pandas 2.3.3, numpy 2.4.6, scipy 1.17.1, Python 3.13.9"
  compute: "1 CPU, under 0.5 GB RAM, seconds for 270 cells x 49 genes (4 perturbations)"
  requires-gpu: "false"
  scheduler: "none"
  requires-network: "install"
  requires-secrets: "none"
---

# Compare each perturbation with the non-targeting control

`scripts/reference.py` is the core of a Perturb-seq report. For each perturbation it compares
that perturbation's cells with the one non-targeting control group, using
`sc.tl.rank_genes_groups(..., groups=[pert], reference=CONTROL, method="wilcoxon")` in a loop over
the perturbation column. Unlike a two-group condition study, many perturbations share a single
reference, so a per-cluster one-vs-rest test (AiScientist's `run_de`) does not answer the
question. The script writes one DE table per perturbation, a summary table with a
self-knockdown positive control, and the genes that move the same way in two or more
perturbations, and prints a JSON summary.

The most likely mistake is running it on every guide. In a pooled screen most guides are silent,
and testing them all spends power and fills the report with noise. Rank the perturbations first
(the `rank-perturbations-by-edistance` skill) and set `ONLY_PERTURBATIONS` to its hits.

Tested on synthetic data only (`tests/`: 270 cells, 49 genes, a non-targeting control of 80
cells; one knockout that loses its own target and switches on a 5-gene program, one silent
guide, one guide with 10 cells, one guide that switches on the same program without losing its
target; and a guide-level variant with two 20-cell guides of one gene) with scanpy 1.12.1,
anndata 0.12.16, pandas 2.3.3, numpy 2.4.6, scipy 1.17.1 and Python 3.13.9. It has been the
AiScientist template for this step of the Perturb-seq pipeline; no real-screen run is recorded
here.

## 1. Environment setup

```bash
mamba create -y -n scanpy_1.12 -c conda-forge python=3.13 scanpy=1.12.1 anndata=0.12.16
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate scanpy_1.12
python -c "import scanpy; print(scanpy.__version__)"
```

`pip install scanpy==1.12.1 anndata==0.12.16` in a Python 3.12+ venv works too. Inside an
AiScientist run, the analysis image already has scanpy.

## 2. Prepare inputs

- An AnnData file with **log-normalized** expression in `X` (the Wilcoxon fold changes assume
  log1p data) and a guide or perturbation label per cell in an `obs` column. The script reads
  `adata_qc.h5ad` from `$AISCIENTIST_WORK` (it keeps the original `obs` labels), else the file
  named by `$AISCIENTIST_DATASET`.
- `$AISCIENTIST_ARTIFACTS` is where the tables go (`tables/` is created).

Find the screen design in the data before configuring:

1. **The perturbation column**: a usually high-cardinality `obs` column naming the guide or
   target per cell (`perturbation`, `guide`, `gRNA`, `sgRNA`, `target`, `target_gene`,
   `gene_target`, `knockout`, `feature_call`). Dozens or hundreds of levels are what separate a
   screen from a two-group condition dataset.
2. **The non-targeting control level**: `NT`, `NTC`, `non-targeting`, `control`, `ctrl`,
   `sgLacZ`, `sgGFP`, `sgScramble`, `scramble`, `unperturbed`, `none`. State which level you
   chose. If it is genuinely ambiguous, ask rather than guess: a wrong control mis-references every
   comparison.
3. **Guides or targets**: with several sgRNAs per gene (`TP53_sg1`, `TP53_sg2`), concordant guides
   of the same gene are biological replicates. Collapsing them to the target gene adds power when
   guide-level groups are small.
4. **No perturbation column?** If guide identity lives in a separate guide-count layer, `obsm` or
   a feature-barcode matrix, cells must be assigned to a guide first (max-count or demultiplexing).
   That is a separate step. Never invent a perturbation column.

Count cells per perturbation and keep the control cells through QC: every comparison is against
them.

## 3. Configure

Edit the values at the top of the script:

| Variable | Meaning | Default |
| --- | --- | --- |
| `PERT_KEY` | the `obs` column naming the guide or perturbation | `perturbation` |
| `CONTROL` | the shared non-targeting level of `PERT_KEY` | `NT` |
| `ONLY_PERTURBATIONS` | `None` for every non-control level, or a list (the E-distance hits) | `None` |
| `COLLAPSE_GUIDE_TO_TARGET` | `True` maps `TP53_sg1`, `TP53-sg1`, `TP53_2`, `TP53-2` to `TP53` (strips one trailing `_` or `-`, optional `sg`, digits); the control level is left as is | `False` |
| `MIN_CELLS` | a perturbation with fewer cells is skipped; a control with fewer stops the run | `30` |
| `LFC` | \|log2 fold change\| threshold for a significant gene | `1.0` |
| `PADJ` | adjusted p-value threshold | `0.05` |

Before collapsing, print the mapping from guide to target once. Control guides named `NT_1`,
`NT_2` collapse into `NT`, which is usually what you want. A label without a guide suffix whose
gene symbol itself ends in `-<n>` loses it (`NKX2-1` becomes `NKX2`), so check symbols such as
`NKX2-1` or `KRTAP1-1`.

To use the cells left after removing escapers (the `filter-escapers-with-mixscape` skill), change
the checkpoint line to read `adata_mixscape.h5ad` instead of `adata_qc.h5ad`. Change the
thresholds only with a reason, and say so in the report.

## 4. Run

```bash
export AISCIENTIST_WORK=/path/to/work AISCIENTIST_ARTIFACTS=/path/to/results
# or, with no adata_qc.h5ad in the work directory:
export AISCIENTIST_DATASET=/path/to/screen.h5ad
python scripts/reference.py
```

In AiScientist: read the file with `read_skill_reference`, set the values for this dataset, and
run it with `run_code`, which sets the variables.

Memory: the AnnData is loaded once and only one two-group subset (one perturbation plus the
control) exists at a time, freed after each perturbation. Do not rewrite the loop to hold every
subset at once: a large screen then runs out of memory and is killed. Give large screens a job
with a real memory limit.

## 5. Validate before using the output

Outputs under `$AISCIENTIST_ARTIFACTS/tables/`:

| Path | Contents |
| --- | --- |
| `perturbation_DE/DE_<perturbation>.csv` | every gene's statistics for one perturbation vs control, sorted by `pvals_adj` |
| `perturbation_DE_summary.csv` | per perturbation: `n_cells`, `n_control`, `n_DEG`, `n_up`, `n_down`, `target_self_knockdown`, `skipped` |
| `shared_up_across_perturbations.csv`, `shared_down_across_perturbations.csv` | genes significant in the same direction in two or more perturbations, most shared first |

Check, in this order:

1. **The JSON summary**: `control`, `level` (guide or target), `n_perturbations_tested` and
   `n_skipped_low_cells`. Every skipped perturbation is in the summary table with
   `skipped = too_few_cells`; list them in the report.
2. **The positive control** (`target_self_knockdown`): a working knockout or knockdown shows its
   own target gene down. `down` passes; `NOT_down(lfc=...)` is listed in
   `failed_self_knockdown_positive_control` and points to a mislabel or no editing. A silent
   guide that also fails it most likely never edited. The check runs only when the label is a
   gene symbol in `var_names`, so guide-level labels such as `TP53_sg1` give `n/a`; collapse to
   targets to get it. Two limits: in a CRISPRa screen the target should go **up**, so read
   `NOT_down` there as expected; and a Cas9 knockout does not always lower the transcript
   (it depends on nonsense-mediated decay), so a `NOT_down` knockout is weaker evidence than a
   `NOT_down` CRISPRi guide.
3. **Each DE table**: fold changes of a few units, not tens (tens suggest raw counts in `X`).
   Mitochondrial, ribosomal or stress genes at the top of many perturbations suggest a quality
   difference between the perturbation's cells and the control rather than biology.
4. **Shared genes**: programs that several perturbations move the same way are candidate shared
   pathways or modules. They are hypotheses, not findings.

The JSON `next` hint suggests enrichment on each strong perturbation's up and down gene lists
(AiScientist: `run_enrichment`); send gene symbols only.

## Report

The perturbation column, the control level, guide or target level, `MIN_CELLS`, the thresholds,
and every perturbation skipped for low cell count. Per tested perturbation: cell count,
`n_DEG` (up/down), the top genes with log fold change and adjusted p-value, never gene names
alone, and the self-knockdown result; flag every guide that fails it. Say whether escaping cells
were removed first (Mixscape) or the DE ran on all guide-assigned cells (conservative, dilutes
effects). Silent perturbations are a result, not a failure. Cells are not independent replicates,
so the Wilcoxon p-values are optimistic; with several replicate lanes or donors, say so. Never
fabricate a gene, fold change, pathway or perturbation, and frame the biology as hypotheses to
validate.
