---
description: Selects compare-perturbations-to-control for a request it should handle.
tags: [trigger, crispr-screens]
runs: 3
max_turns: 4
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

Perturb-seq of about 60 transcription factor knockouts in K562: the `perturbation` column holds sgRNA names like KLF1_sg1 and KLF1_sg2, plus `non-targeting`. For each knocked-out gene I want the genes that go up or down compared with the non-targeting cells, one table per knockout, and a check that each guide actually lowered its own target.
