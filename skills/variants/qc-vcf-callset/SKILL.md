---
name: qc-vcf-callset
description: Judge whether a germline VCF callset is trustworthy before interpreting any variant - Ti/Tv, Het/Hom, SNP, indel and multiallelic counts, sample count and genotype call rate from bcftools stats (falling back to cyvcf2, then to a plain-Python Ti/Tv scan) - and flag values outside the expected human WGS or WES ranges. Writes tables/vcf_qc_summary.csv and data/vcf_qc.json with a qc_flags list. Use when a VCF (one sample or a cohort) arrives for annotation or prioritization, when a Ti/Tv or Het/Hom value needs interpreting, or when deciding whether downstream variant tables must carry a low-confidence caveat.
license: MIT
compatibility: Python 3.11+. bcftools (bioconda) for the full metrics; cyvcf2 as a fallback; with neither, only Ti/Tv and counts. No GPU, no scheduler.
metadata:
  category: variants
  version: "1.0.0"
  status: community
  author: "Yijun Sun"
  aliases: "vcf_qc_stats"
  tags: "vcf, qc, callset-qc, ti-tv, het-hom, call-rate, bcftools, cyvcf2, wgs, wes"
  tested-with: "bcftools 1.24, htslib 1.23.1, cyvcf2 0.34.0, numpy 2.5.4, Python 3.12.15 (plain-Python path also on 3.13.9)"
  compute: "1 CPU, under 100 MB RAM, about 1 s for a 5-record, 2-sample VCF"
  requires-gpu: "false"
  scheduler: "none"
  requires-network: "install"
  requires-secrets: "none"
---

# QC a VCF callset

`scripts/reference.py` computes callset-level QC metrics and flags anything outside the expected
range. It tries `bcftools stats` first (all metrics), then cyvcf2 (no multiallelic count), then a
plain-Python scan that gives only Ti/Tv and the SNP and indel counts. It writes
`tables/vcf_qc_summary.csv` and `data/vcf_qc.json`, which records the `method` used and a
`qc_flags` list.

Run it before interpreting individual variants. A low Ti/Tv or an off-range Het/Hom means the
downstream consequence and pathogenicity tables describe a noisy callset: excess false positives,
contamination, or a sample swap. An off-range Ti/Tv is the strongest single quick signal of a
callset heavy with false positives. The most likely mistake is the wrong `SEQ_TYPE`: an exome
callset judged against the WGS band (or the reverse) is flagged, or passed, for the wrong reason.

Adapted from the variant-calling-vcf-statistics protocol of
[operon](https://github.com/swaruplab/operon), which also gives the expected ranges below.

Tested on synthetic data only (`tests/`: a 2-sample VCF of 4 SNPs and 1 deletion with known
genotypes, run through each of the three methods, plus a 3-SNP VCF judged as WGS and as WES) with
bcftools 1.24, htslib 1.23.1, cyvcf2 0.34.0 and Python 3.12.15 on macOS arm64; the plain-Python
path also with Python 3.13.9. It has been an AiScientist skill since July 2026.

## 1. Environment setup

```bash
mamba create -y -n vcfqc -c conda-forge -c bioconda bcftools=1.24 cyvcf2=0.34.0 python=3.12
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate vcfqc
bcftools --version | head -1   # bcftools 1.24
```

Without bcftools the script falls back to cyvcf2; with neither, it still runs on the standard
library but gives no genotype metrics.

## 2. Prepare inputs

- The VCF (`.vcf` or `.vcf.gz`). The script reads `$AISCIENTIST_DATASET`, else
  `$AISCIENTIST_WORK/normalized.vcf.gz` (the output of a normalization step).
- Every record is counted, whatever its `FILTER`. To judge the calls you will actually use, QC a
  PASS-only copy:

  ```bash
  bcftools view -f .,PASS -Oz -o /path/to/calls.pass.vcf.gz /path/to/calls.vcf.gz
  ```

## 3. Configure

| Variable | Meaning | Default |
| --- | --- | --- |
| `AISCIENTIST_DATASET` | the VCF to QC (`INPUT_VCF` in the script) | `$AISCIENTIST_WORK/normalized.vcf.gz` |
| `AISCIENTIST_SEQ_TYPE` | `WGS` or `WES` (`SEQ_TYPE`); sets the Ti/Tv band; any other value uses the WGS band | `WGS` |
| `AISCIENTIST_ARTIFACTS` | where `tables/` and `data/` are written | `.` |

The expected ranges, for human germline calls (operon), and when the script flags:

| Metric | WGS | WES | Flagged when |
| --- | --- | --- | --- |
| Ti/Tv | about 2.0-2.1 | about 2.8-3.3 | WGS below 1.8 or above 2.5; WES below 2.5 or above 3.5 |
| Het/Hom | 1.5-2.0 | 1.5-2.0 | outside 1.5-2.0 |
| Call rate | above 95% | above 95% | below 90% |

The bands live in `TITV_BAND`, `HETHOM_BAND` and `CALLRATE_MIN` at the top of the script. They do
not apply to somatic or non-human calls; change them only with a reason, and report it.

## 4. Run

```bash
export AISCIENTIST_DATASET=/path/to/calls.vcf.gz AISCIENTIST_SEQ_TYPE=WES
export AISCIENTIST_ARTIFACTS=/path/to/results
python scripts/reference.py
```

In AiScientist: read the script with `read_skill_reference`, set `INPUT_VCF` and `SEQ_TYPE`, and
run it with `run_code`. `annotate_variants` reports the PASS/non-PASS split but nothing about
callset quality, so run this first; route a flagged callset's caveat to Diagnostics, not to the
manuscript's conclusions.

## 5. Validate before using the output

1. `method` in `vcf_qc.json`: only `bcftools stats` and `cyvcf2` give Het/Hom and call rate. The
   plain-Python scan leaves them `null`; say so rather than reporting them as passed.
2. `n_records`, `n_samples`: match what you expect of the file.
3. `ti_tv`, then `het_hom` and `call_rate`, against the bands above.

How the metrics are defined, which matters when comparing runs:

- Call rate is called genotypes (hom-ref, het and hom-alt) over all genotypes, records times
  samples. Missing calls (`./.`) are the only thing that lowers it.
- Het/Hom is heterozygous over homozygous-alternate genotypes, pooled over all samples. With
  bcftools it counts SNPs only; with cyvcf2 it counts every record, indels included, so the two can
  differ. Pooling can hide one outlier sample in a cohort: the per-sample `PSC` lines of
  `bcftools stats -s - /path/to/calls.vcf.gz` show each sample. Het/Hom also depends on ancestry,
  so read the band as a guide to outliers, not a pass mark.
- Ti/Tv: bcftools counts every ALT allele of a multiallelic site; cyvcf2 and the plain-Python scan
  count only the first. The plain-Python scan counts every record whose REF and ALT are not both a
  single base as an indel, MNPs included.

## Report

Ti/Tv with the sequencing type and the method used, Het/Hom and call rate when available, the
record, SNP, indel and sample counts, and every entry of `qc_flags`. If anything was flagged,
frame the downstream variant tables as describing a lower-confidence callset.
