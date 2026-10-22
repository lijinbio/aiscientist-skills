---
description: Selects rank-perturbations-by-edistance for a request it should handle.
tags: [trigger, crispr-screens]
runs: 3
max_turns: 4
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

We ran a pooled CRISPRi screen with a single-cell RNA readout: about 300 guides plus non-targeting controls, guide labels in `obs["guide"]`. Most guides probably did nothing. Before any differential expression, how do I find out which perturbations actually shifted the transcriptome, with a proper significance test?
