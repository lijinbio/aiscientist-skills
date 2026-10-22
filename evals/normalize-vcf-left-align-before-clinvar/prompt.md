---
description: Selects normalize-vcf-with-bcftools for a request it should handle.
tags: [trigger, variant-normalization]
runs: 3
max_turns: 4
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

I have a GRCh38 exome VCF called with FreeBayes, full of indels and with some multiallelic sites. A deletion in a repeat that ClinVar lists as pathogenic comes back as not in ClinVar after annotation. Before I annotate again with VEP and match against ClinVar and gnomAD, I want every indel shifted to its leftmost position and the multiallelic records broken up. How do I do that?
