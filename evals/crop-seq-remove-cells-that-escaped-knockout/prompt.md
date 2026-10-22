---
description: Selects filter-escapers-with-mixscape for a request it should handle.
tags: [trigger, crispr-screens]
runs: 3
max_turns: 4
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

I have a CROP-seq knockout screen in THP-1 cells as a log-normalized AnnData, with a `gene_target` column and `NT` for the non-targeting guides. I suspect many guide-assigned cells were never actually knocked out and they are watering down my comparisons. Before I compare each knockout with the control, can you find the cells that escaped the perturbation and drop them?
