---
description: Selects qc-vcf-callset for a request it should handle.
tags: [trigger, qc]
runs: 3
max_turns: 4
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

A sequencing core sent us a germline whole-exome VCF for 12 samples. Before we look at any individual variant, I want to know whether the calls themselves look trustworthy: the transition/transversion ratio, the het/hom ratio and how many genotypes are missing, and whether any of that is out of range for exome data.
