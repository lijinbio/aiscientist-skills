---
description: Selects qc-snrna-with-cellqc-standalone for a request it should handle.
tags: [trigger, qc]
runs: 3
max_turns: 4
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

I have four 10x Cell Ranger snRNA-seq libraries from mouse cortex (GRCm39). Before integration I need ambient RNA correction, mitochondrial filtering and doublet removal across the cohort using CellQC. How should I set this up and run it on our Slurm cluster?
