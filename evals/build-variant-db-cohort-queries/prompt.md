---
description: Selects build-variant-db-with-tiledbvcf for a request it should handle.
tags: [trigger, variant-database]
runs: 3
max_turns: 4
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

We have about 2,000 single-sample VCFs (bgzipped, indexed, GRCh38) from a population study, and more arrive every month. Re-merging them with bcftools each time takes too long. I want one database where I can add new samples without re-merging and quickly pull every sample's variants in a handful of gene regions.
