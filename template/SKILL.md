---
name: verb-object-with-tool
description: One or two sentences on what the skill does and when to use it. Name the tool, the input it takes and the output it produces, then list the situations that should trigger it (for example "Use when setting up X, writing a Y config, or diagnosing a failed Z run").
license: MIT
compatibility: Software and system requirements, e.g. bash and conda or mamba; Slurm optional.
metadata:
  category: category-name
  version: "0.1.0"
  status: community
  author: ""
  tags: "tag-one, tag-two"
  tested-with: "tool x.y.z, Python 3.12"
  compute: "8 CPUs, 32 GB RAM, 30 min for N samples"
  requires-gpu: "false"
  scheduler: "none"
  requires-network: "install"
  requires-secrets: "none"
---

# Title

What the tool is, what it takes in and writes out, and the one thing most likely to go wrong.

State what this skill was tested on: data (organism, assay, number of samples), versions,
resources and runtime. Replace every `/path/to/...` with your own paths.

## 1. Environment setup

```bash
mamba create -y -n tool_vX.Y.Z -c conda-forge -c bioconda tool=X.Y.Z
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate tool_vX.Y.Z
tool --version
```

## 2. Prepare inputs

How to stage or generate inputs from metadata, and how to check them before running.

## 3. Configure

Only the values that differ from the defaults, each with the reason.

## 4. Run

Dry run first, then local and Slurm variants. Include sizing from the tested run.

## 5. Validate before using the output

Which output files to check, in what order, and what a bad result looks like.

## Report

What to include when reporting the result. Keep "the run completed" separate from
"the result can be trusted".
