---
name: write-variant-tables
description: Write the five standard variant-annotation result tables - consequence, impact and ClinVar-significance distributions, a ClinVar pathogenic and likely-pathogenic list, and a shortlist of rare, damaging variants not in ClinVar - plus a JSON summary, from an annotated per-variant TSV (VEP consequence and impact, SIFT, PolyPhen, max population AF, rsID, ClinVar significance), in pure Python without re-parsing the VCF or re-running VEP. Use when a study needs these tables with a different rarity cutoff, impact set or damaging-predictor rule, or when rebuilding them from an existing annotation table. In AiScientist, annotate_variants already writes the default tables, so use this only for a custom cut.
license: MIT
compatibility: Python 3.11+, standard library only. No GPU, no scheduler, no network.
metadata:
  category: variants
  version: "1.0.0"
  status: community
  author: "Yijun Sun"
  aliases: "variant_output_tables"
  tags: "variant-annotation, vep, clinvar, gnomad, result-tables, rare-variants"
  tested-with: "Python 3.12.15 and 3.13.9 (standard library only)"
  compute: "1 CPU, under 100 MB RAM, well under 1 s for 5 variants"
  requires-gpu: "false"
  scheduler: "none"
  requires-network: "none"
  requires-secrets: "none"
---

# Write the standard variant result tables

`scripts/reference.py` reads `tables/variant_annotation.tsv` (one row per annotated variant) and
writes five tables to `tables/` and a summary to `data/annotated_results_summary.json`. It works
from the table alone: it does not re-parse the VCF or re-run VEP. Standard library only (`csv`,
`json`, `collections`), so there are no pandas dtype pitfalls. Adapt its thresholds and run it;
do not rewrite it from scratch.

The most likely mistake is reading the shortlist as "all candidate variants": it holds only
variants with no ClinVar record at all, so a rare, damaging ClinVar VUS is not on it, and ClinVar
pathogenic calls are in their own table. Absence from ClinVar is not evidence of benignity.

Tested on synthetic data only (`tests/`: 5 variants covering the shortlist, the pathogenic table, a
common variant and a ClinVar VUS, plus a missing and an empty table) with Python 3.12.15 and
3.13.9. It has been an AiScientist skill since July 2026.

## 1. Environment setup

Any Python 3.11 or newer; no packages to install.

```bash
python3 --version   # 3.11 or newer
```

## 2. Prepare inputs

A tab-separated table at `$AISCIENTIST_ARTIFACTS/tables/variant_annotation.tsv` with one row per
variant and these columns: `location`, `allele`, `gene_symbol`, `gene_id`, `consequence`, `impact`,
`amino_acids`, `sift`, `polyphen`, `max_af`, `rsid`, `clinical_significance`. Other columns are
ignored. `max_af` is the highest population allele frequency as a decimal, blank when there is no
record; `clinical_significance` is the ClinVar significance as VEP writes it, blank when not in
ClinVar.

In AiScientist, `annotate_variants` writes this table. Elsewhere, build it from your own
annotation (for example a VEP run with ClinVar and gnomAD) with these column names.

## 3. Configure

Edit the values at the top of the script only if the study needs other cutoffs:

| Variable | Meaning | Default |
| --- | --- | --- |
| `RARE_AF` | rare when AF is below it; a blank or unreadable AF also counts as rare (novel) | 0.001 (0.1%) |
| `HIGH_IMPACT` | VEP impacts that count as damaging | `{"HIGH"}` |
| `DAMAGING_POLYPHEN` | PolyPhen calls that count as damaging | `probably_damaging`, `possibly_damaging` |

A variant is damaging when its impact is in `HIGH_IMPACT`, its SIFT call starts with
`deleterious`, or its PolyPhen call is in `DAMAGING_POLYPHEN`.

The outputs:

| File | Content |
| --- | --- |
| `variant_consequence_distribution.csv` | count and percentage of all variants per consequence (blank: `unknown`) |
| `variant_impact_distribution.csv` | the same per VEP impact (blank: `unknown`) |
| `variant_clinical_significance.csv` | the same per ClinVar significance (blank: `not_in_clinvar`) |
| `clinvar_pathogenic_variants.csv` | significance exactly `pathogenic` or `likely_pathogenic` (case-insensitive); columns Gene, Position, rsID, Disease |
| `high_priority_variants.csv` | no ClinVar record, rare and damaging; columns Gene, Position, rsID, Consequence, Impact, gnomAD_AF, SIFT, PolyPhen, ClinVar_Status |

The `Disease` column holds the ClinVar significance string, not a condition name; this matches
the table AiScientist's `annotate_variants` writes. A combined significance such as
`pathogenic/likely_pathogenic` is not an exact match, so it is left out of the pathogenic table:
look for such values in `variant_clinical_significance.csv`. In the summary,
`n_rare_variants_af_lt_0.1` counts variants with AF below 0.1% (novel ones included).

## 4. Run

```bash
export AISCIENTIST_ARTIFACTS=/path/to/results
python scripts/reference.py
```

In AiScientist: `annotate_variants` already writes these five tables with the default cutoffs, and
its own `high_priority_variants.csv` is broader (it also carries the ClinVar pathogenic calls and
extra columns). Use this script only for a custom cut: read it with `read_skill_reference`, change
the cutoffs, and run it with `run_code`, which sets `AISCIENTIST_ARTIFACTS`. Note that it writes to
the same file names in `tables/`, replacing the tool's versions.

## 5. Validate before using the output

1. `total_variants` in the summary equals the number of rows in the input table.
2. The three distributions each sum to `total_variants`.
3. If `max_af` is blank in most rows, nearly every variant counts as rare: check that the
   frequency annotation ran before trusting the shortlist.
4. `clinical_significance_distribution`: any combined or unusual ClinVar value that should have
   reached the pathogenic table.

## Report

The cutoffs used, the total, the consequence and impact distributions, the number of ClinVar
pathogenic or likely-pathogenic variants and how many were not in ClinVar (saying that absence
from ClinVar is not evidence of benignity), and the shortlist with gene, position, consequence,
frequency and predictor calls.
