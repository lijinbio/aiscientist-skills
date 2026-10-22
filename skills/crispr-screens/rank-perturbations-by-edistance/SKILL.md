---
name: rank-perturbations-by-edistance
description: Rank the perturbations of a pooled CRISPR screen with single-cell readout (Perturb-seq, CROP-seq, CRISPRi or CRISPRa) by E-distance (energy distance) to the non-targeting control in PCA space, with a label-permutation test and Benjamini-Hochberg correction, from an AnnData with a guide or perturbation column to a ranked CSV, the list of hits to carry into differential expression, and an optional perturbation-by-perturbation distance matrix. Use when asking which guides actually changed the transcriptome, when separating real hits from silent guides before per-perturbation DE, or when grouping perturbations with similar effects.
license: MIT
compatibility: Python 3.12+ with scanpy and anndata (conda or pip). No GPU, no scheduler.
metadata:
  category: crispr-screens
  version: "1.0.0"
  status: community
  author: "Yijun Sun"
  aliases: "perturbation_edistance"
  tags: "crispr, perturb-seq, crop-seq, scrna-seq, e-distance, energy-distance, permutation-test, scperturb"
  tested-with: "scanpy 1.12.1, anndata 0.12.16, pandas 2.3.3, numpy 2.4.6, scikit-learn 1.9.0, Python 3.13.9"
  compute: "1 CPU, under 0.5 GB RAM, seconds for 270 cells x 60 genes with 1000 permutations; about 0.1 s per perturbation per 1000 permutations with 2000 control cells and 30 PCs"
  requires-gpu: "false"
  scheduler: "none"
  requires-network: "install"
  requires-secrets: "none"
---

# Rank perturbations by E-distance to the control

In a pooled screen most guides are silent: the guide did not edit, or the gene is dispensable in
this context. `scripts/reference.py` answers "which perturbations actually did something?" before
any differential expression. It measures how far each perturbation moved its cells away from the
non-targeting control in PCA space (the scPerturb E-distance, Peidli et al., *Nat. Methods* 2024),
tests the shift with a label permutation, corrects with Benjamini-Hochberg, and writes a ranked
table, the hits for the DE step (`compare-perturbations-to-control`, `ONLY_PERTURBATIONS`) and,
optionally, a perturbation-by-perturbation distance matrix.

The most likely mistake is keeping `N_PERM = 1000` for a large screen. The smallest permutation
p-value is 1/(N_PERM + 1), so after Benjamini-Hochberg over *m* tested perturbations a lone hit
needs N_PERM + 1 > *m* / FDR. With 1000 permutations and FDR 0.05 that holds only up to 50 tested
perturbations; for 1000 perturbations use at least 20 000. The second most likely is reading the
ranking by distance alone: under no effect the distance is larger for smaller groups (see
section 5), so read it with the permutation p-values.

Tested on synthetic data only (`tests/`: 270 cells, 60 genes, a non-targeting control of 80
cells, two guides that switch on the same 5-gene program, one silent guide and one 10-cell
guide; plus a 30-cell and a 300-cell silent guide, and a check against the pairwise definition)
with scanpy 1.12.1, anndata 0.12.16, pandas 2.3.3, numpy 2.4.6, scikit-learn 1.9.0 and Python
3.13.9. It has been the AiScientist template for this step of the Perturb-seq pipeline; no
real-screen run is recorded here.

## What the statistic is

E(P,C) = 2·δ(P,C) − δ(P,P) − δ(C,C), where δ(X,Y) is the mean squared Euclidean distance over
all pairs of a cell of X and a cell of Y. The script computes it in closed form from group means
and variances (O(n·d) memory, no n×n matrix), so it is exact and scales to large screens. The
means include each cell paired with itself, and then E(P,C) = 2·‖mean(P) − mean(C)‖²: with
squared Euclidean cost the statistic measures a shift of the centroid, not a change of shape.

| Implementation | Same number as this script? |
| --- | --- |
| scPerturb `edist(..., dist="sqeuclidean", sample_correct=False)` | yes |
| scPerturb `edist` defaults (`sample_correct=True`, within-group means over n(n−1) pairs) | no: smaller by 2·Var(P)/(n_P − 1) + 2·Var(C)/(n_C − 1) |
| pertpy `Distance(metric="edistance")` (checked in pertpy 1.4.0) | no: it uses plain Euclidean distances |

A variant sensitive to the shape of the distribution needs non-squared Euclidean distances and
subsampled pairwise distances. Say which definition you used when you compare numbers across
tools.

Significance: for each perturbation the script pools its cells with the control cells, shuffles
the two labels `N_PERM` times, counts how often the shuffled E-distance reaches the observed one
(plus one for the observed, Davison-Hinkley), and applies Benjamini-Hochberg across the tested
perturbations. A perturbation not significant at `FDR` is **silent**.

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

- An AnnData file with a guide or perturbation label per cell in an `obs` column. The script
  reads, in this order, `adata_clustered.h5ad` or `adata_qc.h5ad` from `$AISCIENTIST_WORK`, else
  the file named by `$AISCIENTIST_DATASET`.
- It uses the first `N_PCS` columns of `obsm["X_pca"]` when present (a clustered checkpoint
  has it). Otherwise it runs `sc.pp.pca(adata, n_comps=N_PCS)` on `X`, which should then be
  log-normalized (HVG-subset if you like).
- `$AISCIENTIST_ARTIFACTS` is where the tables go (`tables/` is created).

Identify the perturbation column and the non-targeting control level from the data (column names
such as `perturbation`, `guide`, `sgRNA`, `target_gene`, `feature_call`; control levels such as
`NT`, `NTC`, `non-targeting`, `control`, `sgLacZ`, `sgGFP`, `scramble`), state which you chose,
and ask if it is ambiguous. Count cells per perturbation. If guide identity is not in `obs`,
assign cells to guides first; never invent the column. The PCA must include the control cells.

## 3. Configure

Edit the values at the top of the script:

| Variable | Meaning | Default |
| --- | --- | --- |
| `PERT_KEY` | the `obs` column naming the guide or perturbation | `perturbation` |
| `CONTROL` | the shared non-targeting level of `PERT_KEY` | `NT` |
| `N_PCS` | PCA dimensions the distance is measured in | `30` |
| `MIN_CELLS` | perturbations with fewer cells are counted but not tested | `30` |
| `N_PERM` | label permutations per perturbation; `0` gives distances only, no calls | `1000` |
| `FDR` | Benjamini-Hochberg threshold on the permutation p-values | `0.05` |
| `PAIRWISE` | also write the perturbation-by-perturbation E-distance matrix | `False` |
| `SEED` | seed of the permutations | `0` |

Set `N_PERM` from the number of perturbations you will test (above). The cost grows linearly
with `N_PERM`, the number of perturbations, and the cells in each perturbation plus the control.
The script works at whatever level `PERT_KEY` holds; to work at target-gene level, collapse the
guide labels into a new column first and point `PERT_KEY` at it.

## 4. Run

```bash
export AISCIENTIST_WORK=/path/to/work AISCIENTIST_ARTIFACTS=/path/to/results
# or, with no checkpoint in the work directory:
export AISCIENTIST_DATASET=/path/to/screen.h5ad
python scripts/reference.py
```

In AiScientist: read the file with `read_skill_reference`, set the values for this dataset, and
run it with `run_code`, which sets the variables.

## 5. Validate before using the output

Outputs under `$AISCIENTIST_ARTIFACTS/tables/`:

| Path | Contents |
| --- | --- |
| `perturbation_edistance.csv` | tested perturbations sorted by `edistance`, with `n_cells`, `perm_pvalue`, `perm_padj`, `significant` |
| `perturbation_edistance_pairwise.csv` | with `PAIRWISE = True`: symmetric matrix of E-distances between perturbations with at least `MIN_CELLS` cells |

Check, in this order:

1. **The JSON summary**: `n_perturbations`, `n_tested`, `n_skipped_low_cells`, `n_significant`.
   Perturbations below `MIN_CELLS` are counted but not in the table; list them yourself from the
   cell counts, because the report must name them.
2. **The permutation floor**: if every hit has `perm_pvalue` = 1/(N_PERM + 1) and nothing passes
   `FDR`, the permutations, not the data, limited the call. Raise `N_PERM`.
3. **Distance against group size**: with no effect the expected E-distance is about
   2·V·(1/n_P + 1/n_C), V being the total variance of the PCs used. A 30-cell silent guide
   therefore sits higher in the ranking than a 300-cell silent guide (the tests show it). The
   permutation null has the same group sizes, so `perm_padj` is the call; the distance is the
   effect size among the called hits.
4. **Silent perturbations**: not significant means no detectable transcriptional effect at this
   depth. It is a result: report it, and do not run downstream biology on it.
5. **`real_hits_for_DE`**: the significant perturbations, for `ONLY_PERTURBATIONS`. With
   `N_PERM = 0` it is every tested perturbation ranked by distance, with nothing called.
6. **Pairwise matrix**: a small distance between two perturbations means a similar shift, a
   candidate shared pathway or module. Frame it as a hypothesis.

## Report

The perturbation column, the control level, guide or target level, `N_PCS`, `MIN_CELLS`,
`N_PERM`, `FDR` and the E-distance definition (squared Euclidean, self-pairs included). The
ranked perturbations with E-distance, permutation p-value and adjusted p-value, never names
alone. The silent perturbations, and every perturbation skipped for low cell count. Keep "the
ranking ran" separate from "the hits are real": a hit that also fails its self-knockdown check in
the DE step needs a second look.
