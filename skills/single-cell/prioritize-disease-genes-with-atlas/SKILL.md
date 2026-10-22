---
name: prioritize-disease-genes-with-atlas
description: Prioritize disease-associated genes by combining an existing condition-vs-control differential expression result (per cell type) with a precalculated cell-type atlas, offline. The atlas (long-form CSV, TSV or Parquet profiles, or an h5ad of profiles or of cells) adds cell-type expression specificity and, when present, an independent disease direction; these and the DE effect (plus FDR when the p-values are inferential) form a ranking score, written to tables/atlas/candidates.csv with a figure and a JSON summary. Use after a pseudobulk or reference-group DE, when an atlas can add independent cell-type evidence, when mapping mouse or Ensembl IDs onto a human atlas, or when checking candidates against a known-gene panel. It refuses one-vs-rest marker tables and computes no DE itself.
license: MIT
compatibility: Python 3.11+ with pandas, numpy and matplotlib; anndata and scipy for an h5ad atlas or query; pyarrow for a Parquet atlas. No GPU, no scheduler, no network at run time.
metadata:
  category: single-cell
  version: "1.0.0"
  status: community
  author: "Karry1123"
  aliases: "atlas_disease_genes"
  tags: "scrna-seq, snrna-seq, differential-expression, disease-genes, cell-atlas, gene-prioritization"
  tested-with: "pandas 2.3.3, numpy 2.4.6, matplotlib 3.10.9, anndata 0.12.16, scipy 1.17.1, Python 3.13.9"
  compute: "1 CPU, under 1 GB RAM (0.3 GB peak), seconds for 3-gene tables and a 123-cell atlas"
  requires-gpu: "false"
  scheduler: "none"
  requires-network: "install"
  requires-secrets: "none"
---

# Prioritize disease genes with a cell-type atlas

`scripts/reference.py` takes a condition-vs-control DE result that already exists (one row per
cell type and gene) and a precalculated cell-type atlas, maps both to one gene namespace, and
ranks each DE gene by a weighted evidence score: the DE effect, the DE FDR when the p-values are
inferential, how specific the gene is to the matching atlas cell type, and whether the atlas's
own disease contrast points the same way. It writes a candidate table, a skipped-group table, a
positive-control check and a bar chart, and prints a JSON summary.

The most likely mistake is feeding it a **one-vs-rest marker table**. Markers are cell-type
specific by construction and would top the list as "disease genes", so the script refuses a table
labelled as markers and any table no DE tool labelled, unless you declare it a contrast. The
second is reading the score as a statistic: it is a ranking heuristic, not a probability or an
adjusted p-value, and atlas expression specificity is not a disease-association p-value.

Tested on synthetic data only (`tests/`: a 3-gene DE table over two cell-type groups, a 3-cell-type
profile atlas with a disease contrast, and a 123-cell h5ad atlas as counts or log1p, dense or
sparse) with pandas 2.3.3, numpy 2.4.6, matplotlib 3.10.9, anndata 0.12.16, scipy 1.17.1 and
Python 3.13.9. The Parquet reader is not covered by the tests. Contributed to AiScientist by
Karry1123.

## 1. Environment setup

```bash
mamba create -y -n scanpy_1.12 -c conda-forge python=3.13 scanpy=1.12.1 anndata=0.12.16
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate scanpy_1.12
python -c "import anndata, scipy, matplotlib, pandas; print(anndata.__version__)"
```

scanpy pulls in every package the script uses. Add `pyarrow` for a Parquet atlas. Inside an
AiScientist run, the analysis image already has them. The script never downloads anything: every
atlas and mapping file must be on disk before it runs.

## 2. Prepare inputs

All paths in `CONFIG` are absolute or relative to `$AISCIENTIST_WORK`. Results go under
`$AISCIENTIST_ARTIFACTS`.

**The upstream DE result** sits in `$AISCIENTIST_ARTIFACTS/tables/`, under a key you name in
`CONFIG["de_key"]` (never discovered):

| File | Contents |
| --- | --- |
| `de_<key>_all.csv` | required: columns `group, gene, log2fc, pval, pval_adj, score`; `group` is the cell type |
| `de_<key>_universe.txt` | every tested gene, one per line: the positive control's background (else the genes in the table, with a warning) |
| `pseudobulk_all.csv` | byte-identical to `de_<key>_all.csv` when it came from a pseudobulk test |
| `de_<key>_inference.json` | the label a reference-group DE leaves: `mode`, `reference`, `inference` |
| `de_<key>_<group>.csv`, `rank_<key>_index.csv` | full per-group tables and their group index, preferred over the capped combined table |

Which DE to run first. With independent samples or donors, run a pseudobulk test (AiScientist:
`run_pseudobulk_de`): it tests at the sample level and its p-values gate and score. Otherwise run
a cell-level reference-group contrast stratified by cell type (AiScientist:
`run_de(reference=..., stratify_by=...)`). Its p-values are labelled `exploratory_ranking`, and
the script then gates and scores on effect size and atlas evidence only, never on FDR, and says
so. A pseudobulk combined table keeps only the 500 lowest-p genes per group; genes beyond them
are not ranked (the summary warns). A hand-written contrast table that no tool labelled (for
example from compare-conditions-by-celltype) needs `CONFIG["de_is_condition_contrast"] = True`.

**The atlas.** One of:

- a long-form table (`.csv`, `.tsv`, `.csv.gz`, `.tsv.gz`, `.parquet`) with `cell_type`, `gene` and
  **linear** `mean_expression`, plus optional `disease_log2fc` and `disease_pval_adj` columns that
  add independent directional evidence;
- an `.h5ad` of precalculated profiles (one observation each, linear);
- an `.h5ad` of cells as a researcher uploads it (more than `max_atlas_profiles` observations). It
  is read in row chunks, restricted to the query's genes, and averaged per `cell_type` on the
  linear scale: counts are CP10k-normalised, log1p is undone. Cell types with fewer than
  `min_atlas_cells` cells are dropped and named. A cell-level atlas contributes expression
  context only: it carries no disease contrast unless a table supplies one.

If the atlas has no disease contrast, the ranking rests on query DE plus atlas expression context;
say so.

**Mapping files** (offline, CSV): `ensembl_id,symbol` for an Ensembl namespace (version suffixes
are stripped), `mouse_symbol,human_symbol` for mouse-to-human orthologs. A source ID that maps to
more than one target is excluded and counted in the warnings.

**Optional**: the query `.h5ad` (only checked for cell count and the cell-type column), and a
positive-control panel, one gene symbol per line, `#` lines ignored.

## 3. Configure

Inspect the DE table and the atlas first, then edit `CONFIG` at the top of the script:

| Key | Meaning | Default |
| --- | --- | --- |
| `de_key` | the upstream contrast's key: the `<key>` of `de_<key>_all.csv` | `None` (required) |
| `de_is_condition_contrast` | accept an unlabelled table as a condition contrast | `False` |
| `atlas_path` | atlas file; `None` reads `$AISCIENTIST_REFERENCE` | `None` |
| `query_path` | optional query h5ad; `None` to skip | `adata_qc.h5ad` |
| `atlas_columns` | atlas column names for `cell_type`, `gene`, `mean_expression`, `disease_log2fc`, `disease_pval_adj` | same names |
| `atlas_expression_scale` | h5ad `X` scale: `auto`, `counts`, `log1p`, `linear`; a table must be linear | `auto` |
| `max_atlas_profiles` | an h5ad with more observations is a cell-level object | `5000` |
| `min_atlas_cells` | cell-level h5ad: drop a cell type with fewer cells | `20` |
| `query_species`, `atlas_species` | `human` or `mouse` | `human` |
| `query_gene_namespace`, `atlas_gene_namespace` | `symbol` or `ensembl` | `symbol` |
| `query_id_map_path`, `atlas_id_map_path`, `ortholog_map_path` | the mapping files above | `None` |
| `cell_type_map` | DE group to atlas `cell_type` where the names differ; identity otherwise | `{}` |
| `query_cell_type_column` | `obs` column checked in the query h5ad | `cell_type` |
| `fdr_max`, `min_abs_log2fc` | DE gates (FDR only when p-values are inferential) | `0.05`, `0.25` |
| `min_atlas_mean`, `min_gene_overlap` | atlas expression gate; warn below this many shared genes | `0.0`, `1` |
| `weights` | `fdr`, `effect`, `specificity`, `atlas_concordance` | `0.35, 0.25, 0.25, 0.15` |
| `positive_control_path` | known-gene panel; off unless the phenotype makes it relevant | `None` |
| `top_n_plot` | bars in the figure | `20` |

The positive control is off by default. Set it only when the studied phenotype makes a panel
relevant, for example RetNet for inherited retinal disease (AiScientist ships one as
`gene_panels/ird_retnet.txt`). Its overlap is validation, not an input to the score.

How the score is built, each component scaled to [0, 1]: FDR = −log10(adjusted p) / 10; effect =
|log2FC| / 4; specificity = atlas tau (across all atlas cell types) × the target cell type's share
of the gene's atlas expression; atlas concordance = 1 when the atlas disease log2FC has the same
sign and its adjusted p is at most `fdr_max`. Missing atlas disease DE contributes zero. When the
upstream p-values are labelled `exploratory_ranking` or `pseudoreplicated`, the FDR weight is set
to zero and the rest renormalised. A row is `selected` when it passes |log2FC| ≥ `min_abs_log2fc`,
atlas mean > `min_atlas_mean` and, for inferential p-values only, adjusted p ≤ `fdr_max`.

## 4. Run

```bash
export AISCIENTIST_WORK=/path/to/work AISCIENTIST_ARTIFACTS=/path/to/results
export AISCIENTIST_REFERENCE=/path/to/atlas.h5ad   # or set CONFIG["atlas_path"]
python scripts/reference.py
```

The legacy names `BIOAGENT_WORK` and `BIOAGENT_ARTIFACTS` are still accepted. Without `de_key`
the script stops and lists the DE keys on disk.

In AiScientist: read this file and the script with `read_skill_reference`, inspect the dataset
and atlas metadata, adapt `CONFIG`, and run it with `run_code`. `run_code` sets the work and
results variables and passes the file attached to the run as reference data as
`AISCIENTIST_REFERENCE`. Any other atlas, and every mapping file, must sit under
`AISCIENTIST_WORK`: on the cluster the container sees nothing else.

Outputs:

| Path | Contents |
| --- | --- |
| `tables/atlas/candidates.csv` | every scored DE row: group, gene, atlas cell type, log2FC, adjusted p, atlas mean, `atlas_tau`, `atlas_target_fraction`, `atlas_direction_concordant`, `selected`, `candidate_score`, `why_selected` |
| `tables/atlas/skipped_groups.csv` | DE groups with no matching atlas cell type or no shared genes |
| `tables/atlas/positive_control.csv` | panel size, panel genes in the universe, top-20 hits, expected hits, hypergeometric p |
| `figures/atlas/top_candidates.png` | top selected candidates by score |

The script writes no `de_*` table of its own. For pathway enrichment, run it on the upstream
contrast (AiScientist: `run_enrichment(groupby=<de_key>)`; the summary's `enrichment_groupby`),
so the enrichment reads the same table and its inference label, never this ranking.

## 5. Validate before using the output

1. `de_source` and `p_values_inferential` in the summary: the tool and inference label the table
   was read as. `exploratory_ranking` means the FDR played no part.
2. `warnings`: unmapped or ambiguous IDs, dropped atlas cell types, a missing universe file, the
   500-gene pseudobulk cap, an unlabelled table accepted by declaration.
3. `skipped_groups`: a DE cell type with no atlas match was not scored at all; fix it with
   `cell_type_map`. `overlap_genes` near zero means a namespace or species mismatch.
4. `atlas`: for an h5ad, `kind`, `scale_used` and `cells_per_type`. A cell-level atlas read with
   the wrong scale gives meaningless means.
5. `candidates.csv`: read `why_selected` for the top rows; a top candidate whose atlas disease
   direction disagrees deserves a sentence.
6. `positive_control`, if configured: `top_k_hits` against `top_k_expected`. It validates the
   ranking; it did not shape it.

## Report

The upstream contrast (`de_key`, the tool, its inference label), the atlas (file, kind, scale,
cell types used, whether it has a disease contrast), the gene mappings and how many rows they
lost, the weights and gates, the top candidates with their `why_selected`, the skipped groups,
and the positive-control result if one was set. Call the score an evidence ranking, never a
p-value or a probability that a gene causes the disease.
