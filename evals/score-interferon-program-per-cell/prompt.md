---
description: Selects score-gene-signatures-with-scanpy for a request it should handle.
tags: [trigger, gene-signature]
runs: 3
max_turns: 4
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

I want an interferon-response score for every cell in my clustered mouse AnnData, using IFNG, STAT1, GBP1, CXCL10, IRF1 and ISG15, and then compare that score across cell types and genotypes. Please give me the per-cell scores and a per-group summary I can plot.
