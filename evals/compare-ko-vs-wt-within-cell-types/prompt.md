---
description: Selects compare-conditions-by-celltype for a request it should handle.
tags: [trigger, differential-expression]
runs: 3
max_turns: 4
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

My mouse retina snRNA-seq object already has cell-type labels in `majorclass` and the genotype in `sampleid` (KO and WT). I need KO versus WT differential expression separately within each cell type, a volcano plot for each one, and a list of genes that change in the same direction in several cell types. I'd like to run pathway enrichment on the per-cell-type results afterwards.
