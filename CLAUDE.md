# AiScientist Skills

Registry of Agent Skills (`skills/<category>/<skill-name>/SKILL.md`) used by AiScientist,
plus the `aiscientist-skill` tooling in `src/aiscientist_skills/`.

- Follow [CONTRIBUTING.md](CONTRIBUTING.md) when adding or editing a skill. Scaffold with
  `aiscientist-skill new <category>/<name>`.
- Only include code copied from runs that completed successfully. Never invent commands.
- After any change under `skills/`, `evals/` or `.claude-plugin/`, run
  `aiscientist-skill sync` then `aiscientist-skill validate`.
- Don't hand-edit generated content: the README between `BEGIN SKILLS` / `END SKILLS`, the
  `skills` arrays in `marketplace.json`, and `catalog.json`.
- For tooling changes: `ruff check . && ruff format . && pytest`.
- The tooling is installed with `pip install -e '.[dev]'` (or `uv sync`, then prefix commands
  with `uv run`). Don't make docs, hooks or scripts depend on uv; CI uses `uv.lock` only to pin
  dependency versions.
- New skills start as `status: community`; never promote a tier in the same change that adds
  a skill unless the owner asked for it.
