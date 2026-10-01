# Changelog

All notable changes to this repository are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the registry uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- The `aiscientist-skill` tooling no longer assumes uv. It installs with `pip install -e '.[dev]'`,
  pipx, uv or conda, the docs show the bare command, the pre-commit hook runs whatever
  `aiscientist-skill` is on `PATH`, and CI adds an "Install with pip" job. `uv.lock` remains the
  pin for CI's own dependency versions.
- Docs show how to install the CLI straight from GitHub (`pip install git+https://…`, pipx,
  `uvx --from`), pinned to a release tag.
- Test matrix now covers Python 3.11 and 3.14; the package declares support through 3.14.
- Registry framing: skills for scientific data analysis, with computational biology as the first
  category.

### Added

- `single-cell/qc-snrna-with-cellqc-standalone` 1.0.0 (core): CellQC cohort QC for 10x
  snRNA-seq with bash and conda only, tested with cellqc 0.3.6 (DoubletFinder 2.0.6,
  Snakemake 9.22.0, Python 3.12.14).
- `aiscientist-skill` CLI: `new`, `validate`, `sync`, `list`, `test`, `eval`, `review`,
  `package`, `site`.
- JSON Schema for skill frontmatter, with registry fields (status tier, version, compute,
  scheduler, network, secrets) in `metadata`.
- Content checks for personal paths, emails, real Slurm accounts and tokens.
- Generated `catalog.json`, README catalog and Claude Code plugin marketplace.
- CI (validate, lint, dependency audit, test matrix, permission review), on-demand trigger
  evals, tagged releases with reproducible zips and checksums, and a searchable catalog site.
- Governance (tiers, review, versioning, releases), security policy, code of conduct,
  citation metadata, CODEOWNERS, Dependabot.
- Catalog site with status pills, declared requirements, tag filtering and copyable install
  commands; CI build job that packages release assets on every change.
