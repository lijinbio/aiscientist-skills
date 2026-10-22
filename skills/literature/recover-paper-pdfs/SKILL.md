---
name: recover-paper-pdfs
description: Recover and assemble a corpus of scientific paper PDFs from a list of PMIDs or DOIs through a ladder of legal sources (open-access APIs, PMC and Europe PMC, publisher open access, then the user's institutional access through the campus network, VPN or library discovery search), verifying every PDF and tracking each paper in a manifest. Use when someone needs to download, recover, back-fill or assemble full-text PDFs from PMIDs or DOIs, especially to build a literature corpus for RAG or PaperQA, when papers are paywalled and need institutional access, or when they say "download these papers", "get the full-text PDFs" or "the missing papers". Use it even for a few papers; the value is trying the cheap open sources first and escalating only when needed.
license: MIT
compatibility: A workstation with Python, curl and poppler (pdfinfo, pdftotext); ocrmypdf and pypdf for scans and bundles; a browser for the institutional rungs. No GPU, no scheduler.
metadata:
  category: literature
  version: "1.0.0"
  status: community
  author: "Ziyao Ma"
  aliases: "literature-corpus-recovery"
  tags: "literature, pdf, pubmed, open-access, corpus, rag, paperqa"
  tested-with: "a 1,749-PMID corpus run (2026): NCBI E-utilities, Unpaywall, OpenAlex, Semantic Scholar, poppler, ocrmypdf, pypdf, Chrome (versions not recorded)"
  requires-gpu: "false"
  scheduler: "none"
  requires-network: "runtime"
  requires-secrets: "none"
---

# Recover paper PDFs

Given a list of papers (PMIDs and/or DOIs), get a clean full-text PDF for each, **cheapest and most
open source first**, escalating to institutional access only when needed, and record every outcome
so that success is measured by a manifest, not a file count. The most likely mistake is counting
files instead of verified manifest rows: supplements, figure-only files and wrong papers look like
successes until each file is checked.

Built from one real run: the reference list of a curated retinal-disease gene table, **1,749 unique
PMIDs → 1,739 in the final corpus, mostly Versions of Record**. The remaining ~10 had no reachable
full text and were marked `needs_manual`. Most of the long tail is free if the open rungs are tried
first.

## How the 1,749-paper corpus was recovered (worked example)

The path this skill was built from, in the order it ran:

1. **Get the target list.** Pull the PMIDs from the source table and remove duplicates
   (**1,749 unique PMIDs**).
2. **PMID → metadata.** Query NCBI E-utilities for title, journal, year, **DOI** and **PMCID**, and
   scaffold one manifest row per paper. The manifest is the source of truth from here on.
3. **Sweep the free rungs first (no login).** Open-access APIs (Unpaywall, OpenAlex, Semantic Scholar
   by DOI) plus the **PMC OA PDF** picked up the whole open-access long tail automatically.
4. **Publisher direct PDF from the institution's network.** For subscription journals, the
   publisher's own direct-PDF URL (Wiley `pdfdirect`, Springer `content/pdf`, Taylor & Francis, BMJ
   `.full.pdf`, Neurology `pdfdirect`, IOVS/ARVO). Most Versions of Record came from here.
5. **ScienceDirect / Elsevier in a browser, the largest single method.** One paper at a time: open
   the DOI, wait for ScienceDirect, and click *View PDF*.
6. **The library discovery search (Primo) by DOI, the rescue for "paywalled" papers.** Papers that
   looked locked at the publisher were often held by the library through an aggregator (ProQuest,
   JSTOR, Ovid, EBSCO). Searching **by exact DOI** rescued old *Science*, *Diabetes Care*,
   *Ophthalmic Genetics*, *Retinal Cases* and *OSLI Retina* papers.
7. **Reconcile PMC → journal.** Wherever a paper was held as a PMC or author-manuscript copy but a
   journal Version of Record was reachable, the PMC copy was **replaced** (old file moved to
   `_superseded/`, never deleted).
8. **Verify every file, then fix the failures.** The eight checks below, run over the whole corpus,
   found a **figure-only** file, several **supplement-only** files, one **wrong paper** (right DOI,
   different article inside), ~20 **image-only scans** (OCR'd to add a text layer) and a couple of
   multi-article **bundles** (trimmed to the target).
9. **The last stubborn few.** For papers with no PDF at their own DOI, look for the **same article in
   a different journal**; hand the last ones to the user for a manual download from PubMed's
   **FULL TEXT LINKS**. What still has no full text is marked `needs_manual`.

## The ladder: prefer the journal Version of Record

**Guiding rule:** for each paper, get the **publisher's Version of Record (VoR)** whenever one is
reachable. A PMC copy is fine **only when it is the VoR** (open-access journals deposit the final
published PDF in PMC). The non-VoR sources (Europe PMC full text, a PMC author manuscript, a PMC
HTML or scan reconstruction) are a **last resort**. When a paper has both a PMC copy and a journal
version and they differ, keep the journal version.

| Rung | Source | Gives the VoR? | How |
|---|---|---|---|
| 1 | Open-access APIs | Yes, for OA papers | Unpaywall / OpenAlex / Semantic Scholar by DOI → the OA PDF URL they return |
| 2 | PMC OA PDF | Yes, when the journal is OA | PMID → PMCID → `pmc.ncbi.nlm.nih.gov/articles/PMC<id>/pdf/`; only the published PDF, not an "Author manuscript" banner version |
| 3 | Bookshelf / GeneReviews | Yes | `www.ncbi.nlm.nih.gov/books/NBK<id>/` → the official PDF link |
| 4 | Publisher OA direct PDF | Yes | the publisher's own direct-PDF URL (patterns in `references/publisher-access.md`) |
| 5 | Direct PDF from the institution's network | Yes | the same URLs from a campus IP or the institution's VPN |
| 6 | Browser with institutional login | Yes | click *View PDF* at the publisher; the library discovery search by DOI → aggregator |
| 7 | Internet Archive | Yes (archived VoR) | defunct OA journals: an archived copy via `web.archive.org` |
| 8 | Repositories / preprints | No: author or accepted manuscript | institutional repository, bioRxiv, medRxiv; only if 1–7 fail |
| 9 | Europe PMC full text, PMC HTML or scan reconstruction | **No: last resort** | only when no VoR is reachable |

Rungs 4–6 are where the VoR usually comes from: reach for them **before** the free non-VoR
fallbacks (8–9).

**Before giving up on a "no-PDF" paper, try the same article in a different journal.** The same
content is sometimes published or reprinted under a second DOI that does have a real PDF. Search the
**exact title** on PubMed or Google Scholar. Real example: PMID 21686617 is a *BMJ Case Reports*
record with no PDF anywhere, but the identical case report appeared in *J Neurol Neurosurg
Psychiatry* with a normal VoR; use that and record the alternate DOI.

A handful will still have no reachable VoR (subscription or fellowship wall, SSO-only, defunct DOI,
no PDF anywhere). Record the reason, then either use the best available copy (author manuscript >
reconstruction, noting the tier) or, if the requester wants VoR only, mark the row `needs_manual`.

**Manual fallback for the last few.** Open `https://pubmed.ncbi.nlm.nih.gov/<PMID>/` and use the
**FULL TEXT LINKS** box: a "Free article" tag or a publisher or PMC icon is the direct route. The
user downloads the PDF and drops it into the ingest folder. This is also how a reviewer spot-checks,
so it doubles as the acceptance test.

## 1. Environment setup

```bash
mamba create -y -n paper-recovery -c conda-forge python=3.12 poppler ocrmypdf pypdf requests
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate paper-recovery
pdftotext -v
```

The institutional rungs need a browser. Set it to *download PDFs instead of opening them* and turn
off *ask where to save each file*, so one click drops the PDF into the download folder.

## 2. Prepare inputs

- The list of PMIDs and/or DOIs, deduplicated.
- A manifest (CSV or TSV) with one row per paper: PMID, DOI, PMCID, title, journal, year, `status`,
  `rung`, `version_tier`, `file`, `note`. Fill the metadata from NCBI E-utilities
  (`esummary`/`efetch`) and the PMCID from the PMC ID converter.
- An ingest folder for the PDFs and a `_superseded/` folder beside it.

## 3. Configure

| Setting | Why |
|---|---|
| Your email in the Unpaywall request | Unpaywall requires it; it is not a secret |
| VoR only, or best available copy | Decides whether rungs 8–9 are used or the row becomes `needs_manual` |
| The institution's network | Rung 5 works only from a campus IP or a full-tunnel VPN |

## 4. Run

1. **Free VoR sources (rungs 1–3), no login.** Stop at the first source that yields a real PDF,
   verify it (section 5), record the rung, mark the row done.
2. **Publisher and institutional access (rungs 4–6)** for everything still missing:
   - the publisher's OA direct-PDF URL;
   - the same URL from the institution's network. Where the request comes from matters only for
     publishers that authorize by IP: from a server on a campus network, Springer served a
     closed-access PDF to a plain `curl` (checked 2026-10-22), while Taylor & Francis answered 403
     to the same client and Elsevier answered with a page that needs a browser, whatever the IP;
   - a browser with institutional login: click *View PDF* at the publisher, and search the library's
     discovery layer by exact DOI (`references/publisher-access.md`).
3. **Non-VoR fallbacks (rungs 7–9)**, only for papers with no reachable VoR. Record the version tier.
4. **Reconcile PMC vs journal.** For each paper held as a PMC copy, check whether a journal VoR is now
   reachable; if it is and differs, replace the PMC file and move the old one to `_superseded/`.
5. **Skip the truly unavailable few** (citation-only records, defunct DOIs, publish-ahead-of-print).
   Record the reason and move on; do not hammer a paywall.

Work at a human pace at the publisher sites. **Institutional licences usually forbid systematic or
bulk downloading** of subscription content, even by authorized users. For a large corpus, ask the
library first and use the publishers' text-and-data-mining (TDM) routes where they exist
(Elsevier, Springer Nature and Wiley offer TDM access for subscribers).

## 5. Validate before using the output

A download counts only after it passes all eight checks. Run them over the **whole corpus**, not
only the files that look suspicious. Scripted downloads mislabel silently. `pdfinfo` and
`pdftotext` catch most problems.

1. **A real PDF, not an error page.** It starts with `%PDF`, and its text is not a login, CAPTCHA,
   "Are you a robot", "we don't have this article in PDF format" or 404 page.
2. **Complete, not a fragment.** The page count suits the article type. Watch for the figure-only
   failure (a one-page file that is just Figure 1): page 1 should contain article prose, not only a
   figure caption.
3. **Main text, not a supplement.** A supplement marker appears **near the top of page 1** (within
   the first ~300 characters, not necessarily the first line, since a running header often comes
   first) **and the document has no `Abstract`**. Markers, case-insensitive: `Supplementary`,
   `Supplemental`, `Supporting information`, `Online supporting information`, `SI Appendix`,
   `Supp.`, `Suppl.`, `Supp. Methods`, `Supp. Figure`, `Figure S1`, `Table S1`. Do not rely on the
   absence of "methods": a supplement's "Supp. Methods" heading contains it. The usual cause is a
   scripted "find the PDF link" step grabbing the supplement link, or a PMC OA package that holds
   only the supplement. Re-fetch the article through *View PDF*. *Human Mutation* and similar
   journals deposit a separate supplement PDF that is easy to grab by mistake.
4. **The right paper.** Normalize the expected title and check that its distinctive words appear in
   the text. A low match on a full-text file usually means the wrong paper (right DOI in the file
   name, different article inside); re-download by DOI. A low match on a short file is often a
   shared page or a scan without text: inspect it before discarding.
5. **Readable text.** Old papers from PMC, NEJM or BBRC are sometimes image-only: complete pages,
   almost no extractable text. A RAG index cannot read them. Add a text layer with
   `ocrmypdf --force-ocr` (needs tesseract, ghostscript and qpdf) and check that text now extracts.
6. **One article per file.** Some publisher PDFs (a "Letters" section, for example) hold a whole
   multi-article section. Find the target's page range and trim to it with pypdf. If the target
   shares a page with a neighbour and trimming would drop its title, keep the file whole.
7. **The version tier.** Record whether each file is the VoR, an author or accepted manuscript, or a
   reconstruction. A reconstruction is the weakest tier and can carry artifacts (a scrambled
   corresponding-author email, for example): replace it when a real PDF turns up.
8. **Look at page 1.** A VoR shows the publisher masthead (journal logo, "© Publisher", "journal
   homepage"); an author manuscript shows an "Author manuscript" banner; a reconstruction shows its
   capture line; a supplement opens with "Supplementary". Two things look wrong but are fine:
   journals before about 2000 have no logo, only a citation line such as
   `Am. J. Hum. Genet. 49:939-950, 1991`; and in "Letters" or "Correspondence" sections several items
   share printed pages, so page 1 can open with the tail of the previous item and the page numbers
   start at the journal page.

Only then mark the manifest row done, with its rung and version tier. Keep every superseded or
rejected file in `_superseded/`, so the count stays checkable and mistakes are reversible.

## Guardrails

- **Never bypass** CAPTCHAs, logins, paywalls or bot checks, and never mass-download from
  subscription sites. When a site challenges a request, stop and let the user continue by hand.
- **The user performs all authentication**: passwords, two-factor prompts, SSO and any
  "Accept terms" click.
- Use only access the user legitimately has, and keep to the institution's licence terms.
- Prefer the most open source that works; escalate only for what the cheaper rungs miss.
- Track progress from the manifest, never from a file count.

## Report

The number of papers requested, recovered (by rung and by version tier), `needs_manual` (with the
reason for each) and replaced during reconciliation; the checks run and what each found; and the
manifest path. Keep "every paper has a file" separate from "every file passed verification".
