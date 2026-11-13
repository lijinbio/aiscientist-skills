---
name: read-evidence-with-mcp
description: Search citations, retrieve local corpus passages, answer with PaperQA or curate grounded gene evidence through an already configured literature MCP service. Use when that service and the required corpus/model are available and task coverage, citations and partial results must be tracked; retain current retrieval tools when the MCP service is absent.
license: MIT
metadata:
  category: literature
  version: 0.1.0
  status: community
  tags: mcp, literature
  tested-with: aiscientist-mcp-literature 0.0.1, common 0.0.3; real Europe PMC and staged RetiGene/PubMedBERT retrieval, Python 3.12.13; generative acceptance tracked separately
  compute: Public search and local retrieval tested; model answer/curation resources depend on the configured deployment
  requires-gpu: 'false'
  scheduler: optional
  requires-network: runtime
  requires-secrets: none
  mcp-server: literature
  mcp-package-version: 0.0.1
---

# Read scientific evidence with the literature MCP service

Discover the registered `literature` service and its actual tools. If it is unavailable, keep
existing literature tools and installed corpus/PDF skills. Do not assume a prefixed MCP tool
exists or replace a working model credential/billing path. This migration skill has no image
pin and does not install or enable a service by itself.

## Pick a tool by the evidence needed

| Tool | Evidence and scope |
| --- | --- |
| `literature_search` | Public keyword `query`, `limit`, optional `pubmed_only` and `abstracts`; citation discovery through Europe PMC. |
| `search_corpus` | Local `queries`, `terms`, optional `pmids`, `top_k`, `max_per_paper`; verbatim retrieved passages with citation/page and retrieval diagnostics. |
| `deep_literature` | A `question` answered with the configured PaperQA model and prebuilt corpus index; inspect supporting contexts. |
| `extract_haploinsufficient_genes` | Whole-corpus gene-evidence curation, with retrieval/pilot controls, optional `pmids` and a complete typed `spec` for a different property. |

A retrieval hit is evidence to read, not an automatic answer. A top-k search does not establish
whole-corpus completeness. For extraction, retain the `spec` definition, inclusion/exclusion
rules and requests. A positive `max_passages` is a smoke-test cap and must be reported as partial.
Use pilot diagnostics before scaling an expensive curation job.

## Bind the deployed corpus and model

The operator supplies `LITERATURE_CORPUS_ROOT`, admitted roots, PDF/manifest/text/vector paths,
staged PubMedBERT weights and the PaperQA index. Shared corpus assets stay read-only. Queries
may create derived caches only inside the analysis. Do not silently change corpus versions
or model identity while resuming judgments; start a new `analysis_id` for those changes.

`search_corpus` does not call a generative model. Answering and extraction require explicit
server-side model settings; absent settings are a deployment failure, not permission to invent
an answer. Public search sends its keywords to Europe PMC, and PaperQA can request bibliographic
metadata. Keep clinical identifiers out of a public search unless that transmission is intended.
A configured model receives the evidence required by its operation. The model transport supports
OpenAI-compatible endpoints, not native Anthropic `/messages`. Credentials are never tool arguments.
User API-key sessions keep the application's existing trusted credential/billing path.

The standalone server cannot enforce a provider-specific dollar budget: positive
`max_cost_usd` is refused. Use the deployment's spending controls instead of claiming a tool
cap limits costs.

## Finish and validate

All action tools accept `analysis_id` and `rerun`. Poll
`literature_job_status(analysis_id, task_id)` to `COMPLETED` after asynchronous submission;
inline waits in the current allocation. Keep task IDs and failures. A failed or empty evidence
step does not count as a supported finding.

Inspect citation identifiers, actual passages, quote verification, HGNC resolution, coverage,
review flags and unread/pilot diagnostics. Where the response is bounded, `full_result` and
artifact tables contain the complete data; total counts are not the preview length. Distinguish
no retrieved evidence from evidence that contradicts a claim. Report corpus/model versions,
method, limits, task IDs and only citations that support the associated statement.

The native service has real Europe PMC and staged RetiGene/PubMedBERT retrieval checks plus
synthetic protocol/algorithm regression tests. Generative answer and curation deployment
acceptance is a separate gate; these retrieval checks alone do not establish it.
