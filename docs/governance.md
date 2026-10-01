# Governance

How skills enter the registry, how they are trusted, and how releases reach AiScientist.

## Tiers

| Tier | Meaning | How a skill gets there |
| --- | --- | --- |
| ⚪ `community` | Passed every automated gate. Not reviewed by a person. | Default for new contributions. |
| 🔵 `verified` | A domain reviewer has checked the method, the parameters and the validation steps, and confirmed the skill states what it was tested on. | Approval from the category's CODEOWNER. |
| 🟢 `core` | Maintained by the registry owners, who rerun it when the tools it depends on change. | Owner decision. |

The tier is `metadata.status` in `SKILL.md`. Any change to it is flagged by the permission
review, so a PR can't promote itself. Applications decide which tiers to load; a sensible
default is `core` and `verified`, with `community` available on request.

## Review

Automated gates do the routine checking, so human review can focus on the science:

1. **CI** (required): validate, lint, test. See the table in the [README](../README.md#what-runs-on-every-pull-request).
2. **Permission review** (automatic): the baseline is no secrets, network access only to
   install software, no `allowed-tools` grant, no GPU and no executable code in `scripts/`.
   A PR that adds or widens any of these, or changes `scripts/` or a tier, is labeled
   `needs-security-review` and needs an owner's approval.
3. **Domain review**: CODEOWNERS assigns the category's reviewer. They check that the method
   is sound, that the parameters are justified, that the validation steps would catch a bad
   result, and that the code was copied from a completed run.
4. **Evals** (on demand, label `run-evals`): confirm the description makes the skill load for
   realistic requests.

## Versioning

- **Skills** carry their own semantic version in `metadata.version`:
  - **major**: inputs, outputs or defaults change in a way that changes results;
  - **minor**: new optional steps, new reference support;
  - **patch**: wording, fixes that don't change results.
- **The registry** has one version, `metadata.version` in `.claude-plugin/marketplace.json`.
  A release is the tag `v<that version>`; the release workflow refuses a tag that doesn't
  match.

## Releasing

1. Move the `Unreleased` entries in `CHANGELOG.md` under the new version.
2. Bump `metadata.version` in `.claude-plugin/marketplace.json`, then run
   `aiscientist-skill sync`.
3. Merge to `main`, then tag: `git tag v0.2.0 && git push origin v0.2.0`.

The release workflow validates the registry and publishes per-skill zips, `catalog.json` and
`SHA256SUMS` as a GitHub release.

## Runtime responsibilities

This repository declares what each skill needs; the application that runs skills enforces it.
AiScientist should:

- pin a release tag and verify `SHA256SUMS`;
- load only the tiers it trusts;
- grant network access, secrets, GPUs and scheduler access only as each skill's frontmatter
  declares, and inject secrets per run rather than exposing them to skill authors;
- log the skill name and version with every run, and track error rates per version so a
  broken release can be rolled back.
