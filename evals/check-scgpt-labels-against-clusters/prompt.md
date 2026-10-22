---
description: Selects crossvalidate-scgpt-vs-leiden for a request it should handle.
tags: [trigger, cell-type-annotation]
runs: 3
max_turns: 4
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

scGPT gave me a predictions CSV with a label and a confidence for every cell of my raw retina matrix. My clustered h5ad has fewer cells after QC, plus Leiden clusters and the original majorclass labels. When I tried to add the predictions as an obs column I got a length mismatch error. How far can I trust the scGPT labels, cluster by cluster?
