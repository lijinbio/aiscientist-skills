---
description: Selects prioritize-clinical-variants for a request it should handle.
tags: [trigger, variant-prioritization]
runs: 3
max_turns: 4
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

I have a VEP-annotated table of about 180 rare variants from a family with a suspected autosomal recessive retinal dystrophy (columns: consequence, impact, SIFT, PolyPhen, CADD, REVEL, max gnomAD AF, ClinVar significance). Which should we review first? Rank them into tiers using ClinVar, population frequency for a recessive model and the predictors.
