---
description: Selects write-variant-tables for a request it should handle.
tags: [trigger, variant-annotation]
runs: 3
max_turns: 4
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

Our VEP annotation with ClinVar and gnomAD is done and saved as a per-variant TSV. I need the usual summary tables (consequence and impact breakdowns, the ClinVar pathogenic list and a shortlist of rare damaging variants not in ClinVar), but with rare meaning a gnomAD allele frequency below 1% instead of 0.1%.
