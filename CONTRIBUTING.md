# Contributing

Thanks for adding to AiScientist Skills. A skill here is a method someone else can rerun and
trust, so the bar is that it has actually been run. Participation is covered by the
[code of conduct](CODE_OF_CONDUCT.md).

## Quick start

### Install the tooling

`aiscientist-skill` is a plain Python package (Python 3.11 or newer). Use whichever installer
you already work with; the commands in this guide are identical afterwards.

```bash
git clone https://github.com/lijinbio/aiscientist-skills.git && cd aiscientist-skills

pip install -e '.[dev]'          # pip, into your active environment
pipx install -e '.[dev]'         # pipx, isolated and on your PATH
uv sync                          # uv, creates .venv from uv.lock (then `uv run aiscientist-skill …`)
conda create -n aiscientist-skills python=3.12 pip && conda activate aiscientist-skills && pip install -e '.[dev]'

pre-commit install               # optional: run the checks on every commit (pip/pipx/uvx install pre-commit)
```

### Add a skill

```bash
aiscientist-skill new <category>/<skill-name> --author "Your Name"
$EDITOR skills/<category>/<skill-name>/SKILL.md
aiscientist-skill sync           # README catalog, marketplace.json, catalog.json
aiscientist-skill validate       # everything CI checks
```

Then add a trigger eval (below) and open a pull request. If `validate` passes locally, CI will
pass too.

## What makes a good skill

1. **Tested code only.** Copy commands and scripts from a run that completed. Don't reconstruct
   them or write them from documentation.
2. **Say what it was tested on**: data (organism, assay, number of samples), tool versions,
   resources and runtime, in the text and in `metadata.tested-with` / `metadata.compute`.
3. **Self-contained.** Include environment setup (a pinned `mamba create ...`). Put code in the
   skill's own `scripts/`, with tests in its `tests/`.
4. **Reproducible.** Pin versions, set seeds, and generate inputs from metadata.
5. **Validation.** Say which outputs to check, in what order, and what a bad result looks like.
6. **Honest declarations.** Fill in `requires-network`, `requires-secrets`, `requires-gpu` and
   `scheduler` truthfully. They drive the permission review and the runtime sandbox.
7. **No private data.** No patient identifiers, credentials, personal paths, internal hostnames
   or real cluster accounts. Use `/path/to/...`, `<partition>` and `<account>`. `validate`
   catches the common cases.

Instruction-only skills (just `SKILL.md`) are welcome. Many of the most useful skills capture
expertise, not code.

## Frontmatter reference

| Field | Required | Rule |
| --- | --- | --- |
| `name` | yes | lowercase letters, digits, single hyphens, at most 64 characters, same as the folder |
| `description` | yes | 40–1024 characters, no `<` or `>`. What it does **and when to use it**. |
| `license` | yes | SPDX identifier, `MIT` by default |
| `compatibility` | no | system requirements, at most 500 characters |
| `allowed-tools` | no | pre-approved tools; setting it triggers security review |
| `metadata.category` | yes | same as the category folder |
| `metadata.version` | yes | semantic version, e.g. `"1.0.0"` |
| `metadata.status` | yes | `community` for new skills (see [governance](docs/governance.md#tiers)) |
| `metadata.tested-with` | yes | key tool versions of the tested run |
| `metadata.author`, `tags`, `compute` | no | `tags` is comma-separated lowercase |
| `metadata.requires-gpu` | no | `"true"` or `"false"` |
| `metadata.scheduler` | no | `none`, `optional` or `required` |
| `metadata.requires-network` | no | `none`, `install` or `runtime` |
| `metadata.requires-secrets` | no | `none` or comma-separated env var names |

All `metadata` values are strings, so quote `"true"`, `"false"` and versions. The authoritative
definition is the [JSON Schema](src/aiscientist_skills/schemas/skill.schema.json).

**The description matters most.** It is all the agent sees when deciding whether to load the
skill. Name the tool, the inputs, and the situations that should trigger it.

## Trigger evals

Add at least one case per skill under `evals/<case-name>/` (copy an existing one): a
`prompt.md` with a realistic request that doesn't name the skill, and a grader that passes
when the skill is loaded. `validate` warns about skills without one. See
[evals/README.md](evals/README.md).

## Code in skills

If a skill ships `scripts/`:

- Python must pass `ruff check` and `ruff format` (run by CI and pre-commit);
- add `tests/` with pytest tests that run in seconds without large data;
- the change gets the `needs-security-review` label.

## Naming

- Skills: `verb-object[-with-tool]`, e.g. `qc-snrna-with-cellqc-standalone`.
- Categories: a short domain noun, e.g. `single-cell`, `splicing`, `crispr-screens`. A new
  category needs a plugin entry (`name`, `description`) in `.claude-plugin/marketplace.json`
  and a line in `.github/CODEOWNERS`.

## Style

- Keep `SKILL.md` under about 500 lines; move reference material into `references/`.
- Write plainly: what to do, why, and what to check.
- Use fenced code blocks with a language tag, and tables for parameters and outputs.

## Changing an existing skill

Bump `metadata.version` (see [versioning](docs/governance.md#versioning)) and add a line to
[CHANGELOG.md](CHANGELOG.md) under `Unreleased`.
