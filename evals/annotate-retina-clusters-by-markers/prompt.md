---
description: Selects annotate-clusters-by-markers for a request it should handle.
tags: [trigger, cell-type-annotation]
runs: 3
max_turns: 4
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

I have a human retina snRNA-seq AnnData that is already clustered (Leiden, log-normalized, with the full gene set in `.raw`). There is no annotated reference atlas for this tissue that I trust. Can you label each cluster with its cell type from known marker genes? Muller glia and astrocytes share some markers here, so I'd rather leave a cluster unlabeled than get a confident wrong call.
