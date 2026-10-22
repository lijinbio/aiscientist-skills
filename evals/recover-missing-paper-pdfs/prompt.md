---
description: Selects recover-paper-pdfs for a request it should handle.
tags: [trigger, literature]
runs: 3
max_turns: 4
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

I'm building a PaperQA index for our lab's gene list. I have about 400 PMIDs in a spreadsheet and need the full-text PDFs for all of them; some are in subscription journals our university library has access to. How should I go about getting them, and how do I know the files are the right papers?
