# Access methods: endpoints, URL patterns, the discovery layer, gotchas

The concrete "how" for each rung of the ladder in `SKILL.md`. Everything here assumes access the
user legitimately has (the institution's network, VPN or SSO). Never bypass a paywall, CAPTCHA,
bot check or login. `<DOI>` and `<PMID>` are the paper's identifiers.

## Rung 1: open-access APIs (free, no login)

Query by DOI, then download the PDF URL each returns:

- **Unpaywall**: `GET https://api.unpaywall.org/v2/<DOI>?email=YOUR_EMAIL` → JSON →
  `best_oa_location.url_for_pdf` (fall back to `oa_locations[].url_for_pdf`).
- **OpenAlex**: `GET https://api.openalex.org/works/doi:<DOI>` → `open_access.oa_url` (or
  `primary_location.pdf_url`).
- **Semantic Scholar**: `GET https://api.semanticscholar.org/graph/v1/paper/DOI:<DOI>?fields=openAccessPdf`
  → `openAccessPdf.url`.

Always confirm the response is a real PDF (check 1 in `SKILL.md`), not an HTML landing page.

## Rungs 2–3: PMC and Bookshelf (free)

- **PMID → PMCID**: `GET https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids=<PMID>&format=json`.
- **PMC OA PDF**: `https://pmc.ncbi.nlm.nih.gov/articles/PMC<id>/pdf/`. A browser may be needed once
  to clear NCBI's "Preparing to download" page; do not bypass it.
- **PMC OA package** (for figures or supplements, or when the direct PDF is blocked):
  `GET https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC<id>` → a `.tar.gz` with the PDF.
- **GeneReviews / NCBI Bookshelf**: `https://www.ncbi.nlm.nih.gov/books/NBK<id>/` → the page's PDF
  link.

## Rungs 4–5: direct-PDF URL patterns

Rung 4 is the publisher's open-access copy. Rung 5 is the same URL requested from the institution's
network (a campus IP or a full-tunnel VPN), which unlocks subscription content at publishers that
authorize by IP. Some publishers answer a scripted client with a bot check or a page that needs a
browser whatever the IP; then use rung 6.

- **Wiley**: `https://onlinelibrary.wiley.com/doi/pdfdirect/<DOI>?download=true` (FASEB uses the
  `faseb.` subdomain)
- **BMJ (J Med Genet)**: `doi.org` → `jmg.bmj.com/content/<vol>/<iss>/<page>` →
  `https://jmg.bmj.com/content/jmedgenet/<vol>/<iss>/<page>.full.pdf`; BMJ Case Reports →
  `casereports.bmj.com/content/bmjcr/<vol>/<iss>/<page>.full.pdf`
- **Neurology**: `https://www.neurology.org/doi/pdfdirect/<DOI>?download=true` (`/doi/pdf/` only
  shows the reader)
- **ACS**: `https://pubs.acs.org/doi/pdf/<DOI>?download=true`
- **Springer**: `https://link.springer.com/content/pdf/<DOI>.pdf` (served a closed-access PDF to a
  plain request from a campus IP, 2026-10-22)
- **Taylor & Francis**: `https://www.tandfonline.com/doi/pdf/<DOI>?download=true` (403 to a scripted
  client; use a browser)
- **SAGE**: `https://journals.sagepub.com/doi/pdf/<DOI>?download=true` (Cloudflare check: the user
  completes it once in the browser)
- **IOVS / ARVO**: PubMed article page → the "Silverchair" link → `iovs.arvojournals.org/article.aspx?...`
  → the toolbar **PDF**
- **OJS journals** (e.g. viamedica): `doi.org` → the real "Download PDF file" link
  `.../article/download/<id>/<galley>`

## Rung 6: browser with institutional login

### ScienceDirect / Elsevier

- Elsevier resolves by PII: `https://www.sciencedirect.com/science/article/pii/<PII>`. Old-style
  DOIs give the PII by stripping punctuation and upper-casing; `j.`-style DOIs need a `doi.org`
  resolve first to read the PII from the landing URL.
- A green **View PDF** (full-text access) means the institution has the subscription. Click it.
  ScienceDirect does not serve the PDF to a scripted request for the raw PDF URL (it returns a blank
  page); do not try to work around that.
- If a click does not start the download, close the tab left from the previous download and click
  again. If the site starts challenging requests, stop and let the user continue by hand.

### The library discovery search (Ex Libris Primo at many universities)

Many papers that look locked at the publisher are held by the library through an **aggregator**.
In the run this skill comes from, this rescued old *Science*, *Diabetes Care*, *Ophthalmic Genetics*,
*Retinal Cases* and *OSLI Retina* papers.

- Sign in with the institutional account; it also unlocks the interlibrary-loan request button on
  records with no full text.
- **Search by exact DOI.** A title search collides with newer, similarly titled papers.
- If the result row shows **Get PDF** or **Download PDF**, click it: it resolves to ProQuest, JSTOR,
  Ovid, Taylor & Francis or EBSCO with institutional access.
- If it shows only **Available Online**, open the record detail and read its **View Online** section
  for the real provider. The quick link can resolve to an unrelated sign-in page, a dead end.

## Rungs 7–8: archive, repositories, preprints (free, not always the VoR)

- **Internet Archive**: for journals that went defunct but were open access (e.g. *Molecular
  Vision*), find an archived copy of the original PDF URL via `https://web.archive.org/`.
- **Repositories and preprints**: search the DOI or title and take the institutional-repository or
  bioRxiv / medRxiv PDF when one exists. It is an author or accepted manuscript: record the tier.

## Rung 9: last resort, when no VoR is reachable

- **Europe PMC full-text PDF**: `https://www.ebi.ac.uk/europepmc/webservices/rest/PMC<id>/fullTextPDF`
  (or list the options at `.../PMC<id>/fullTextUrlList`).
- **Rebuild from PMC HTML**: capture the article's `<article>` HTML from its PMC page and render it to
  a clean, searchable PDF (39 papers in the run this skill comes from).
- **Scanned pages**: for old scanned articles, capture the page images from the PMC viewer and
  assemble them into one PDF, keeping every page (17 papers in that run).

## Publisher gotchas

Holdings differ between institutions; these are what the run this skill comes from met.

- **ProQuest** wraps old papers as image scans: low extractable text but complete pages (acceptable;
  OCR them). The first download shows a cookie banner and a welcome walkthrough; dismiss both, then
  the **Download PDF** button works.
- **JSTOR** requires a one-time **Accept and download** terms click, which the user makes.
- **Ovid (LWW, Retinal Cases)** often has a single-simultaneous-user licence: a transient
  `License Service Failure (Code: E3)` means the slot is busy; retry in a minute. The discovery
  search's **Download PDF** reaches the subscribed Ovid entry, while a raw `doi.org` link may show
  "Check Access".
- **Healio** differs by journal: *OSLI Retina* was in ProQuest; *J Pediatr Ophthalmol Strabismus*
  had only a link back to the publisher, so it went to interlibrary loan.
- **Publish-ahead-of-print** items are not in a subscribed issue yet: wait for the issue or use
  interlibrary loan.
- **Older ClinicalKey journals** (e.g. *Ophthalmology*, *Am J Ophthalmol*) may have no institutional
  full-text holding: the discovery search shows only a citation record → interlibrary loan.
