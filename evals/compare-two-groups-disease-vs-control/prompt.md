---
description: Selects compare-two-groups-with-scanpy for a request it should handle.
tags: [trigger, differential-expression]
runs: 3
max_turns: 4
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

I have a log-normalized snRNA-seq AnnData of mouse retina with a `condition` column (rd10 and wild type). Which genes are up- or down-regulated in rd10 compared with wild type across all cells? I need a ranked table I can open in Excel.
