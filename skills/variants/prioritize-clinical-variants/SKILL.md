---
name: prioritize-clinical-variants
description: Rank annotated variants into research-triage tiers (ClinVar pathogenic, likely pathogenic, VUS favouring pathogenic, VUS, likely benign, benign) from ClinVar significance used verbatim, gnomAD allele frequency against a dominant or recessive disease-model cutoff and the ACMG BA1 5 percent rule, and in-silico predictors (SIFT, PolyPhen, REVEL, CADD, AlphaMissense) as supporting evidence only. Pure Python; reads a per-variant annotation TSV and writes a tier-sorted CSV with the evidence for each tier plus a JSON of tier counts. Use when a rare-variant list from VEP, ClinVar and gnomAD annotation must be ordered for review (which variants to look at first) or when choosing the disease model and cutoffs for that ordering. Research triage only, NOT a clinical ACMG/AMP classification.
license: MIT
compatibility: Python 3.11+, standard library only. No GPU, no scheduler, no network.
metadata:
  category: variants
  version: "1.0.0"
  status: community
  author: "Yijun Sun"
  aliases: "clinical_variant_prioritization"
  tags: "variant-prioritization, clinvar, gnomad, acmg, rare-disease, vus, in-silico-predictors"
  tested-with: "Python 3.12.15 and 3.13.9 (standard library only)"
  compute: "1 CPU, under 100 MB RAM, well under 1 s for 10 variants"
  requires-gpu: "false"
  scheduler: "none"
  requires-network: "none"
  requires-secrets: "none"
---

# Prioritize annotated variants into research-triage tiers

`scripts/reference.py` reads `tables/variant_annotation.tsv` (one row per annotated variant) and
writes `tables/prioritized_variants.csv`, sorted from the most to the least actionable tier with
the evidence behind each tier, and `data/prioritization_summary.json` with the tier counts and the
caveat below. It needs nothing beyond the Python standard library.

> **Research triage only, not a clinical ACMG/AMP diagnosis.** ClinVar significance is used
> verbatim and never upgraded. Computational predictions are supporting evidence only (ACMG
> PP3/BP4): a rare variant with strong predictions becomes `VUS_FAVOR_PATH`, still a VUS, never
> pathogenic from computation alone. Every prioritized variant needs orthogonal validation
> (segregation, phenotype, expert review) before any clinical use.

The most likely mistake is the wrong disease model: the dominant cutoff (AF below 1e-4) is 100
times stricter than the recessive one (below 1e-2), so the same variant can be `VUS` under one and
`VUS_LIKELY_BENIGN` under the other. Also note that a blank frequency counts as AF 0, so a variant
with no gnomAD record is treated as rare, and that absence from ClinVar is not evidence of
benignity.

Adapted from the `classify_variant()` heuristic of the variant-calling-clinical-interpretation
protocol of [operon](https://github.com/swaruplab/operon) (disease-model AF thresholds, ClinVar and
in-silico predictors).

Tested on synthetic data only (`tests/`: 10 variants covering every tier, under both disease
models, plus a missing and an empty table) with Python 3.12.15 and 3.13.9. It has been an
AiScientist skill since July 2026.

## 1. Environment setup

Any Python 3.11 or newer; no packages to install.

```bash
python3 --version   # 3.11 or newer
```

## 2. Prepare inputs

A tab-separated table at `$AISCIENTIST_ARTIFACTS/tables/variant_annotation.tsv` with one row per
variant. The script uses these columns and ignores the rest:

| Column | Content | Used for |
| --- | --- | --- |
| `clinical_significance` | ClinVar significance as VEP writes it (`pathogenic`, `likely_pathogenic`, `uncertain_significance`, `conflicting_interpretations_of_pathogenicity`, `benign`, ...); blank when not in ClinVar | the ClinVar tiers |
| `max_af` | highest population allele frequency (gnomAD, 1000 Genomes) as a decimal; blank when there is no record | rarity, BA1 |
| `impact`, `consequence` | VEP impact and consequence terms | loss of function |
| `sift`, `polyphen` | VEP SIFT and PolyPhen calls (`deleterious...`, `probably_damaging`, `possibly_damaging`) | predictor hits |
| `revel`, `cadd_phred`, `alphamissense` | predictor scores, optional; blank or absent is fine | predictor hits |
| `gene_symbol`, `location`, `rsid` | copied to the output | |

In AiScientist, `annotate_variants` writes this table with exactly these column names. Elsewhere,
build it from your own annotation (for example a VEP run with ClinVar and gnomAD) with these
column names. Prefer the gnomAD filtering allele frequency (FAF) over the raw AF in `max_af` when
you have it.

## 3. Configure

| Value | Meaning | Default |
| --- | --- | --- |
| `AISCIENTIST_DISEASE_MODEL` (`DISEASE_MODEL`) | `dominant` or `recessive`; sets the rare cutoff | `dominant` |
| `RARE_AF` | rare when AF is below it: dominant 1e-4, recessive 1e-2; any other model uses 1e-4 | from the model |
| `BA1_AF` | above it, a variant not in ClinVar is `LIKELY_BENIGN_COMMON` (ACMG BA1: too common to cause a rare disease) | 0.05 |
| `REVEL_PATH`, `CADD_PATH`, `ALPHAMISSENSE_PATH` | a predictor hit is REVEL above 0.5, CADD phred 20 or more, AlphaMissense above 0.564 | as listed |
| `LOF_CONSEQUENCES` | consequence substrings counted as loss of function, as is `impact` `HIGH` | frameshift, stop_gained, splice_donor, splice_acceptor, start_lost |

SIFT `deleterious` and PolyPhen `probably_damaging` or `possibly_damaging` are hits too. Change a
cutoff only with a reason, and report it.

The tiers, in order of precedence and in the order of the output:

| Tier | Rule |
| --- | --- |
| `PATHOGENIC_CLINVAR` | ClinVar significance is exactly `pathogenic` |
| `LIKELY_PATHOGENIC_CLINVAR` | any other significance containing `pathogenic` but not `conflicting` (`likely_pathogenic`, `pathogenic/likely_pathogenic`) |
| `VUS_FAVOR_PATH` | rare, and loss of function or 2 or more predictor hits |
| `VUS_ELEVATED` | rare, 1 predictor hit |
| `VUS` | rare, no hits |
| `VUS_LIKELY_BENIGN` | AF between the rare cutoff and BA1 |
| `LIKELY_BENIGN_COMMON` | AF above BA1 (0.05) |
| `BENIGN_CLINVAR` | ClinVar significance containing `benign` but not `conflicting` |

ClinVar is checked first, then BA1, then the computed band. `uncertain_significance` and
`conflicting_...` fall through to the computed band: they are never upgraded. The pathogenic check
runs before the benign one, so a combined ClinVar string holding both words without `conflicting`
lands in a pathogenic tier; read such rows.

## 4. Run

```bash
export AISCIENTIST_ARTIFACTS=/path/to/results AISCIENTIST_DISEASE_MODEL=recessive
python scripts/reference.py
```

In AiScientist: run it after `annotate_variants`, when the study wants the actionable variants
ordered rather than the flat `high_priority_variants` shortlist the tool writes. Read the script
with `read_skill_reference`, set `DISEASE_MODEL` for the study, and run it with `run_code`.

## 5. Validate before using the output

1. `total_variants` in the summary equals the number of rows in the input table.
2. If `max_af` is blank in most rows, every one of them counts as rare: check that the frequency
   annotation actually ran before trusting the VUS tiers.
3. The predictor columns are blank unless the annotation added them. With SIFT and PolyPhen only,
   2 hits need both; say which predictors were present.
4. Read the `Evidence` column of the top rows: each computed tier names the AF, the cutoff, the
   predictor hits and the loss-of-function flag behind it.

## Report

The disease model and the cutoffs, the tier counts, then lead the actionable section with the top
tiers (`PATHOGENIC_CLINVAR`, `LIKELY_PATHOGENIC_CLINVAR`, `VUS_FAVOR_PATH`), giving gene, location,
rsID and the evidence for each. Always carry the research-triage caveat, report ClinVar
significance verbatim, and say that absence from ClinVar is not evidence of benignity.
