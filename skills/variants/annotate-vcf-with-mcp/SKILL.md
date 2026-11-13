---
name: annotate-vcf-with-mcp
description: Annotate an admitted VCF through an already configured variant-annotation MCP service using matching offline VEP references, then inspect complete consequence, frequency and ClinVar tables. Use for this service deployment and its asynchronous results; retain the existing VCF workflow when it is unavailable and never silently switch private variants to REST.
license: MIT
metadata:
  category: variants
  version: 0.1.0
  status: community
  tags: mcp, variant-annotation
  tested-with: aiscientist-mcp-variant-annotation 0.0.1, common 0.0.3; native MCP and deterministic VEP/bcftools regression fixtures; release-112.0 VEP image build
  compute: 'Service default: 8 CPUs, 32 GB, 8 hours; reference downloads and real callset acceptance are deployment-specific'
  requires-gpu: 'false'
  scheduler: optional
  requires-network: runtime
  requires-secrets: none
  mcp-server: variant-annotation
  mcp-package-version: 0.0.1
---

# Annotate a VCF through the variant MCP service

Use the client's registered `variant-annotation` service. Tool names are native names below;
discover any host qualification rather than constructing it. Without this service, keep the
current annotation tools and established VCF QC/normalization skills. No existing skill image
is changed by this migration skill, and no unpublished image is assumed available.

## Confirm assembly and input scope

`annotate_variants` accepts `vcf_path` or the operator-bound `VARIANT_DATASET`, `assembly`,
`species`, `mode`, `pass_only`, `max_variants`, `max_pop_af`, `genes`, optional `regions_bed`
and `sample`, plus `analysis_id` and `rerun`. Inspect the live schema for exact types/defaults.
VCF and BED paths must be inside `VARIANT_READ_ROOTS` on the server host.

The default assembly is GRCh38, not an inference from every input. Confirm the real build and
match VEP cache, FASTA and ClinVar releases. The offline server supports human annotation;
licensed/optional predictor assets are separately staged by the operator. Do not claim CADD,
REVEL, AlphaMissense, SpliceAI or another layer ran merely because its columns exist.

## Preserve the execution and privacy choice

Use `mode="offline"` with deployed references. REST requires both the explicit tool mode and
operator `VARIANT_ALLOW_REST=1`; there is no automatic fallback. It sends variant loci/alleles
to Ensembl, has a bounded workload and refuses unsupported sample/BED selection. Keep that
choice separate from a failed offline installation. Offline `max_variants` limits parsed
annotation rows after VEP, so it is not a guarantee of lower annotation compute.

Submit once, retain `analysis_id`, `task_id`, and any Slurm `job_id`, and poll
`variant_job_status` to `COMPLETED`. Inline waits inside the current allocation. Each attempt
has its own artifacts; `rerun=true` creates another attempt after the active one ends.

## Validate delivered annotation

Check whole-file versus retained PASS/non-PASS counts, assembly/reference provenance,
normalization actually performed, sample/region/AF filters, parsed/omitted rows, optional
predictors that ran, and warnings. Read the complete `variant_annotation.tsv`, distributions,
ClinVar findings, rare unclassified candidate table and summary JSON from `artifact_root`.
The native response is a bounded preview; follow `full_result`/omission indicators before
claiming a complete candidate list.

Report variants as research annotations requiring review; classification labels and heuristic
ranks are not a clinical diagnosis. Keep the site validation evidence separate from synthetic
VEP/bcftools executable fixtures and container tools-list smoke checks. Production reference
and website acceptance must precede retiring the original application path.
