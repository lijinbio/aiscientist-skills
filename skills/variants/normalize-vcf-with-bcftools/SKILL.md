---
name: normalize-vcf-with-bcftools
description: Normalize a VCF with bcftools norm before annotation or ClinVar/gnomAD matching - split multiallelic sites into biallelic records, atomize MNPs into SNPs, then left-align and trim indels against the reference FASTA of the same build - writing an indexed normalized.vcf.gz and a JSON of record counts before and after. Use when a VCF not known to be normalized (especially an indel-heavy one) will be matched against ClinVar, gnomAD or dbSNP, compared between callers or loaded into PLINK, or when a known pathogenic indel comes back as not in ClinVar. In AiScientist, the offline annotate_variants path already normalizes, so do not plan it as a separate step there.
license: MIT
compatibility: bcftools from bioconda, bash, and Python 3.11+ (standard library only); a reference genome FASTA matching the VCF's build and contig names. No GPU, no scheduler.
metadata:
  category: variants
  version: "1.0.0"
  status: community
  author: "Yijun Sun"
  aliases: "normalize_vcf"
  tags: "vcf, variant-normalization, bcftools, left-alignment, multiallelic, clinvar, gnomad"
  tested-with: "bcftools 1.24, htslib 1.23.1, Python 3.12.15"
  compute: "1 CPU, under 100 MB RAM, about 1 s for a 4-record VCF on a 60-base reference"
  requires-gpu: "false"
  scheduler: "none"
  requires-network: "install"
  requires-secrets: "none"
---

# Normalize a VCF with bcftools

`scripts/reference.py` runs three `bcftools norm` stages as one pipe: `-m-any` splits multiallelic
sites into biallelic records, `--atomize` splits MNPs into single SNPs, and `-f REF` left-aligns and
trims indels against the reference FASTA. It writes `normalized.vcf.gz` with a `.tbi` index and
`data/normalization_summary.json` with the record counts before and after.

Why it matters: dbSNP, ClinVar and gnomAD store variants in a left-aligned, parsimonious form. An
indel written at the other end of a repeat, or an allele hidden inside a multiallelic record, does
not match its database record, so a real pathogenic variant is reported as `not_in_clinvar` with no
error anywhere. The most likely mistake is a reference FASTA that does not match the VCF: another
build (GRCh37 vs GRCh38) or other contig names (`chr1` vs `1`). bcftools then stops, and the script
reports `bcftools norm failed` with the reason. Left-alignment cannot be done without the reference,
so the script refuses to run without it rather than writing a half-normalized file.

The stage order is deliberate. Atomizing first makes bcftools 1.24 rewrite a multiallelic SNP
`G>A,T` as `G>A,*` and `G>T,*`, and the split then leaves spurious `G>*` records with wrong
genotypes. Splitting first gives clean biallelic records.

Adapted from the variant-calling-variant-normalization protocol of
[operon](https://github.com/swaruplab/operon) (MIT licence, Copyright (c) 2026 Swarup Lab), with the stage order changed as above.

Tested on synthetic data only (`tests/`: a one-sample VCF of 4 records on a 60-base reference,
holding a multiallelic SNP, an MNP, a deletion inside a CA repeat and a plain SNP; 6 records come
out, the deletion moved to the left end of the repeat) with bcftools 1.24, htslib 1.23.1 and
Python 3.12.15 on macOS arm64. It has been an AiScientist skill since July 2026.

## 1. Environment setup

```bash
mamba create -y -n bcftools_1.24 -c conda-forge -c bioconda bcftools=1.24 htslib=1.23.1 python=3.12
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate bcftools_1.24
bcftools --version | head -1   # bcftools 1.24
```

The script also needs `bash`, which runs the three-stage pipe.

## 2. Prepare inputs

- The VCF (`.vcf` or `.vcf.gz`). The script reads `$AISCIENTIST_DATASET`, else
  `$AISCIENTIST_WORK/input.vcf.gz`.
- The reference FASTA of the VCF's assembly. bcftools builds the `.fai` index beside it when it is
  missing and the folder is writable.

Check before running that the contig names agree, and that the build does:

```bash
bcftools view -h /path/to/calls.vcf.gz | grep '^##contig' | head -3
cut -f1,2 /path/to/genome.fa.fai | head -3
```

chr1 is 249250621 bases in GRCh37 and 248956422 in GRCh38.

Skip normalization when the VCF is already normalized, for example a single-caller GATK or DRAGEN
output you know to be left-aligned. Normalizing twice is harmless but wastes time.

## 3. Configure

| Variable | Meaning | Example |
| --- | --- | --- |
| `AISCIENTIST_DATASET` | the input VCF (`INPUT_VCF` in the script) | `/path/to/calls.vcf.gz` |
| `AISCIENTIST_REF_FASTA` | the reference FASTA (`REF_FASTA`), same build and contig names as the VCF | `/path/to/GRCh38.primary_assembly.genome.fa` |
| `AISCIENTIST_WORK` | where `normalized.vcf.gz` and its index are written | `/path/to/work` |
| `AISCIENTIST_ARTIFACTS` | where `data/normalization_summary.json` is written | `/path/to/results` |

Whether a downstream tool needs biallelic records (from the operon protocol): PLINK yes, ClinVar
matching yes, VEP either way, Hail no.

## 4. Run

```bash
export AISCIENTIST_DATASET=/path/to/calls.vcf.gz AISCIENTIST_REF_FASTA=/path/to/genome.fa
export AISCIENTIST_WORK=/path/to/work AISCIENTIST_ARTIFACTS=/path/to/results
python scripts/reference.py
```

The pipe runs as `bash -c` with `set -o pipefail`, so a failure in any stage stops the run, and the
error message includes the stderr of all three stages. Paths are shell-quoted, so file names with
spaces or quotes are safe.

In AiScientist: under the offline annotation path (`AISCIENTIST_VARIANT_ON_HPC`), do not plan a
normalize step. `annotate_variants` already runs `bcftools norm -m-any -f REF` before VEP, which
splits multiallelic sites and left-aligns against the reference; it skips only `--atomize`, a minor
gap for SNV and indel database matching. A separate step could not run there anyway: the `run_code`
sandbox mounts no reference FASTA, so the script stops at its reference check. Never replace this
step with hand-written Python (cyvcf2 or similar): it cannot left-align. Only a REST-path run on a
small, indel-heavy VCF that is known not to be normalized gains from running this first, where
bcftools and the reference are both available; then point `annotate_variants` at
`normalized.vcf.gz`.

## 5. Validate before using the output

1. `records_after` in the summary is at least `records_before`: splitting and atomizing only add
   records. `-1` means bcftools could not read the file to count it.
2. No star alleles came out of the pipe:

   ```bash
   bcftools view -H /path/to/work/normalized.vcf.gz | awk '$5 == "*"' | wc -l   # 0
   ```

   A star allele already in the input (a spanning deletion, `A,*`) comes out as its own `G>*`
   record, so if the count is not 0, check whether the input had star alleles.
3. Look up one indel you know sits in a repeat: its `POS` should be the leftmost equivalent
   position.
4. `normalized.vcf.gz.tbi` exists; region queries need it.

## Report

The input VCF, the reference FASTA and its build, the record counts before and after, and the
path of the normalized VCF that annotation should read. If the step was skipped because the
annotation path normalizes, say so.
