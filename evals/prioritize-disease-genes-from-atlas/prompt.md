---
description: Selects prioritize-disease-genes-with-atlas for a request it should handle.
tags: [trigger, disease-genes]
runs: 3
max_turns: 4
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

I already ran pseudobulk differential expression of rd10 versus wild type for each retinal cell type (the table is in `tables/`). I also have a precalculated human retina atlas with mean expression per cell type plus a disease log2 fold change column. My genes are mouse Ensembl IDs. Which of my DE genes are the strongest disease-gene candidates once the atlas evidence is taken into account?
