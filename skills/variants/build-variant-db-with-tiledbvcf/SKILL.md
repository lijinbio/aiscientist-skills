---
name: build-variant-db-with-tiledbvcf
description: Build and query a TileDB-VCF variant database for a cohort with tiledbvcf-py - ingest many indexed single-sample VCFs into one compressed sparse-array dataset (a re-run adds only new samples, with no re-merging), query genomic regions across all or selected samples, and export the matching records (sample, contig, position, alleles, genotype) to a TSV with per-sample counts. Use when a study has many single-sample VCFs and needs population-scale storage, incremental sample addition or fast region and sample queries instead of repeated bcftools merges. Skip it for a single VCF.
license: MIT
compatibility: Python 3.11+ with tiledbvcf-py (tiledb conda channel) and bcftools or tabix to bgzip and index the inputs. No GPU, no scheduler.
metadata:
  category: variants
  version: "1.0.0"
  status: community
  author: "Yijun Sun"
  aliases: "build_variant_db_tiledbvcf"
  tags: "vcf, tiledb-vcf, variant-database, cohort, population-genomics, region-query"
  tested-with: "tiledbvcf-py 0.40.3, libtiledbvcf 0.40.3, tiledb 2.30.1, bcftools 1.24, htslib 1.23.1, pandas 2.3.3, numpy 2.5.4, Python 3.12.15"
  compute: "1 CPU, under 1 GB RAM, about 1 s for 3 single-sample VCFs of 1-3 records"
  requires-gpu: "false"
  scheduler: "none"
  requires-network: "install"
  requires-secrets: "none"
---

# Build a cohort variant database with TileDB-VCF

[TileDB-VCF](https://github.com/TileDB-Inc/TileDB-VCF) stores many single-sample VCFs in one
sparse-array dataset: samples are added incrementally with no merge step, storage is compressed,
and region and sample queries are fast. `scripts/reference.py` creates the dataset under
`$AISCIENTIST_WORK/variant_db` on the first run and ingests every `*.vcf.gz` in
`$AISCIENTIST_WORK`. On later runs it ingests only the VCFs whose sample the dataset does not hold
yet, because ingesting a sample twice stores its records twice. It then queries two example
regions across all samples, writes the records to `tables/cohort_region_variants.tsv` and prints
the sample count, the record count and the 10 samples with the most records. This is an optional
step for cohorts; skip it for a single VCF.

The most likely mistake is a region that does not match the VCF's contig names or build. The
example regions are TP53 and BRCA2 in GRCh38 coordinates on contigs named `17` and `13`. On VCFs
whose contigs are `chr17` and `chr13`, the query returns 0 records with no error, and GRCh37
coordinates point somewhere else.

Tested on synthetic data only (`tests/`: three single-sample VCFs of 1-3 records on contigs `13`
and `17`, one record outside the regions; ingest and query, a re-run after adding a sample, and
`chr`-prefixed contigs) with tiledbvcf-py 0.40.3 (tiledb 2.30.1), bcftools 1.24, pandas 2.3.3 and
Python 3.12.15 on macOS arm64. A real cohort has not been run through this script. It has been an
AiScientist skill since July 2026.

## 1. Environment setup

```bash
mamba create -y -n tiledbvcf_0.40.3 -c conda-forge -c bioconda -c tiledb \
    python=3.12 tiledbvcf-py=0.40.3 bcftools=1.24 \
    c-blosc2=2.23.1 azure-core-cpp=1.16.2 azure-storage-blobs-cpp=12.16.0 \
    azure-storage-files-datalake-cpp=12.14.0 azure-identity-cpp=1.13.3
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate tiledbvcf_0.40.3
python -c "import tiledbvcf; print(tiledbvcf.version)"   # 0.40.3
```

The `c-blosc2` and `azure-*-cpp` pins were needed on macOS arm64: the `tiledbvcf-py` 0.40.3 package
there bundles a TileDB library linked against those exact versions, and without the pins
`import tiledbvcf` fails with `Library not loaded: @rpath/libblosc2.7.dylib` (or a
`libazure-...` library). Linux was not tested; if the import fails there with a missing shared
library, apply the same pins.

## 2. Prepare inputs

- One bgzipped, indexed VCF per sample (`.tbi` or `.csi`). A multi-sample VCF must be split into
  one file per sample first.

  ```bash
  bcftools view -Oz -o /path/to/work/SAMPLE.vcf.gz /path/to/SAMPLE.vcf
  bcftools index -t /path/to/work/SAMPLE.vcf.gz
  ```

- The script ingests every `*.vcf.gz` in `$AISCIENTIST_WORK`. Keep only the sample VCFs there (a
  `normalized.vcf.gz` from another step would be ingested too), or set `SAMPLE_VCFS` to an explicit
  list.

## 3. Configure

Edit the values in the script:

| Value | Meaning | Default |
| --- | --- | --- |
| `SAMPLE_VCFS` | the single-sample VCFs to ingest | every `*.vcf.gz` in `$AISCIENTIST_WORK` |
| `DATASET_URI` | where the dataset lives | `$AISCIENTIST_WORK/variant_db` |
| `regions=[...]` in `ds.read` | `contig:start-end` strings, with the VCF's contig names and build | TP53 and BRCA2, GRCh38, contigs `17` and `13` |
| `samples=` in `ds.read` | a subset of samples to query (commented out) | all samples |
| `attrs=[...]` in `ds.read` | the fields exported | `sample_name`, `contig`, `pos_start`, `pos_end`, `alleles`, `fmt_GT` |

The dataset is created with `create_dataset()` defaults, which store the common INFO and FORMAT
fields. Only a local directory was tested as `DATASET_URI`. TileDB-VCF also accepts `s3://`,
`az://` and `gs://` URIs, but the script decides whether the dataset exists by looking at the local
filesystem, so replace that check before using a cloud URI.

## 4. Run

```bash
export AISCIENTIST_WORK=/path/to/work AISCIENTIST_ARTIFACTS=/path/to/results
python scripts/reference.py
```

To add samples later, put their VCFs in `$AISCIENTIST_WORK` and run the script again; it prints how
many VCFs it skipped as already ingested.

In AiScientist: the `run_code` analysis image does not include `tiledbvcf-py`, so the script stops at
`import tiledbvcf` there unless the image adds it. Where it is available, read the script with
`read_skill_reference`, set the regions for the study's loci, and run it with `run_code`.

## 5. Validate before using the output

1. The printed sample count equals the number of samples you meant to ingest. A re-run that
   reports more records than before without new samples means something was ingested twice.
2. A record count of 0: compare the region strings with the contig names in a VCF header
   (`bcftools view -h /path/to/work/SAMPLE.vcf.gz | grep '^##contig'`) and with the build.
3. For a large query, check `ds.read_completed()` after `ds.read(...)`. When it is `False`, the
   DataFrame holds only part of the results; use `ds.read_iter(...)`, which takes the same
   `attrs`, `samples` and `regions`, to read them all.
4. `tables/cohort_region_variants.tsv`: genotypes in `fmt_GT` are arrays of allele indexes (`[0 1]`
   is heterozygous, `[1 1]` homozygous alternate).

## Report

The number of samples in the dataset, the regions queried with their build, the number of records
returned and the per-sample counts, and the path of the exported table.
