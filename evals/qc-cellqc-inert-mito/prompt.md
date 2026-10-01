---
description: Selects qc-snrna-with-cellqc-standalone for a request it should handle.
tags: [trigger, qc]
runs: 3
max_turns: 4
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

My CellQC run on macaque nuclei finished, but metrics.csv shows filter_fail_mito = 0 for every library even though I set mito: 5 in config.yaml. What is going on and how do I fix the gene set?
