---
name: filter-escapers-with-mixscape
description: Label and remove escaping cells in a pooled CRISPR screen with single-cell readout (Perturb-seq, CROP-seq) with Mixscape from pertpy, from a log-normalized AnnData with a guide or perturbation column and a non-targeting control to adata_mixscape.h5ad without the non-perturbed (NP) cells, plus the NP fraction of every perturbation. Use before per-perturbation differential expression when guide-assigned cells may have escaped knockout or knockdown and dilute the comparison, or when asked which cells of a screen were actually perturbed. Optional step with a heavy dependency; without pertpy the script exits cleanly and the DE runs on all guide-assigned cells.
license: MIT
compatibility: Python 3.12+ with scanpy, anndata and pertpy 1.4 (pip). No GPU, no scheduler. Without pertpy the script skips and exits 0.
metadata:
  category: crispr-screens
  version: "1.0.0"
  status: community
  author: "Yijun Sun"
  aliases: "mixscape_escape_filter"
  tags: "crispr, perturb-seq, crop-seq, scrna-seq, mixscape, pertpy, escaping-cells"
  tested-with: "pertpy 1.4.0, scanpy 1.12.1, anndata 0.12.16, pandas 2.3.3, numpy 2.4.6, scipy 1.17.1, scikit-learn 1.9.1, pynndescent 0.6.0, numba 0.68.0, Python 3.13.9"
  compute: "1 CPU, 0.85 GB peak RAM, about 12 s for 240 cells x 47 genes (mostly pertpy import and JIT compilation)"
  requires-gpu: "false"
  scheduler: "none"
  requires-network: "install"
  requires-secrets: "none"
---

# Remove escaping cells with Mixscape

In a real screen a fraction of the guide-assigned cells escape knockout or knockdown and look
transcriptionally like control. Keeping them dilutes every downstream comparison.
`scripts/reference.py` runs Mixscape (Papalexi et al., *Nat. Genetics* 2021, as implemented in
pertpy): it computes a local perturbation signature for every cell and classifies each cell as
perturbed (KO), non-perturbed (NP, escaped) or control, then writes the AnnData without the NP
cells for the per-perturbation DE (`compare-perturbations-to-control`).

This step is optional. pertpy is a heavy dependency and its Mixscape API drifts between versions.
If pertpy cannot be imported, the script prints a `SKIPPED` note and exits 0; the DE then runs on
all guide-assigned cells, a conservative, effect-diluting choice that the report must state.

The most likely mistake is reading an NP fraction of 1.0 as "every cell escaped". Mixscape first
looks for genes that differ between the perturbation and the control; with fewer than 5 such
genes it labels the whole perturbation NP. A silent guide therefore loses all its cells here (the
tests show it). That is "no detectable signature", the same result the E-distance ranking calls
silent, and it means the filtered file holds no cells of that perturbation.

Tested on synthetic data only (`tests/`: 240 cells, 47 genes, a non-targeting control of 100
cells; a knockout of 80 cells of which 40 lost the target and switched on a 5-gene program and 40
escaped; and a silent guide of 60 cells) with pertpy 1.4.0, scanpy 1.12.1, anndata 0.12.16,
pandas 2.3.3, numpy 2.4.6, scipy 1.17.1, scikit-learn 1.9.1 and Python 3.13.9. Mixscape kept
exactly the 40 knocked-out cells (NP fraction 0.5), removed all 60 cells of the silent guide and
kept every control cell. The skip path is tested with pertpy made unimportable. No real-screen
run is recorded here.

## 1. Environment setup

```bash
mamba create -y -n pertpy_1.4 -c conda-forge python=3.13 pip
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate pertpy_1.4
pip install scanpy==1.12.1 anndata==0.12.16 pandas==2.3.3 numpy==2.4.6 scipy==1.17.1 pertpy==1.4.0
python -c "import pertpy; print(pertpy.__version__)"
```

The `pip install` line is the one tested, in a plain Python 3.13.9 venv. The first
`import pertpy` takes tens of seconds while it compiles; later imports take a few seconds.

The call to `ms.mixscape` passes the label column and the control by position because pertpy 1.0
and earlier name the label argument `labels` and pertpy 1.4 names it `pert_key`. If your pertpy
rejects the call, read `help(pt.tl.Mixscape.mixscape)` and adapt that one line.

## 2. Prepare inputs

- An AnnData file with **log-normalized** expression in `X` (the signature averages control
  neighbours with `expm1` and returns to `log1p`) and a guide or perturbation label per cell in an
  `obs` column, including the non-targeting control. The script reads `adata_qc.h5ad` from
  `$AISCIENTIST_WORK`, else the file named by `$AISCIENTIST_DATASET`.
- The output goes to `$AISCIENTIST_WORK` as well; this script writes no tables.

Mixscape classifies within each level of the perturbation column, so give it the same level
(guide or target gene) that the DE will use. Identify the column and the control level from the
data as for the DE step, and keep the control cells through QC.

## 3. Configure

| Variable | Meaning | Default |
| --- | --- | --- |
| `PERT_KEY` | the `obs` column naming the guide or perturbation | `perturbation` |
| `CONTROL` | the shared non-targeting level of `PERT_KEY` | `NT` |

The Mixscape calls use pertpy's defaults. In pertpy 1.4.0 those are: the signature of a cell is
its difference from the mean of its 20 nearest control cells, searched in the first 15 PCs
(pertpy computes a PCA if `X_pca` is missing); a perturbation needs at least 5 genes with
adjusted p < 0.05 and |log fold change| ≥ 0.25 against control; and a cell with posterior above
0.5 in the perturbed component is KO. To change them, add keyword arguments to the two calls:
`perturbation_type="KD"` labels CRISPRi cells KD instead of KO (the filter keeps both), and
`split_by="<column>"` runs the steps within each replicate or lane (pertpy's own example uses
`split_by="replicate"`). Record any change in the report.

## 4. Run

```bash
export AISCIENTIST_WORK=/path/to/work
# or, with no adata_qc.h5ad in the work directory:
export AISCIENTIST_DATASET=/path/to/screen.h5ad
python scripts/reference.py
```

In AiScientist: read the file with `read_skill_reference`, set the values for this dataset, and
run it with `run_code`, which sets the variables.

## 5. Validate before using the output

The JSON summary on stdout, and `$AISCIENTIST_WORK/adata_mixscape.h5ad` holding the kept cells
with `obs["mixscape_class"]`, `obs["mixscape_class_global"]` (KO, NP or the control label),
`obs["mixscape_class_p_ko"]` and the signature in `layers["X_pert"]`.

1. **`mixscape`**: `OK`, or `SKIPPED` with the reason. After a skip, the DE runs on all
   guide-assigned cells: say so.
2. **The control**: every control cell is kept; `class_counts` shows them under the control
   label.
3. **`np_fraction_by_perturbation`**: between 0 and 1 for a perturbation with a signature; a
   high fraction means many escapers, or a weak guide. Exactly 1.0 means no signature (above);
   cross-check with the E-distance ranking.
4. **`n_cells_before` and `n_cells_after_removing_NP`**: every perturbation you will test still
   has enough cells for the DE (`MIN_CELLS`, default 30).
5. Point the DE at the filtered file: in `compare-perturbations-to-control`, change the checkpoint
   line to read `adata_mixscape.h5ad`.

## Report

Whether Mixscape ran (with the pertpy version) or was skipped and why; the perturbation column,
the control level and the level (guide or target); any argument changed from pertpy's defaults;
the NP fraction of every perturbation, with the perturbations labelled NP as a whole named as
having no detectable signature; and the cells before and after. If it was skipped, state that
the DE used all guide-assigned cells and that effects may be diluted.
