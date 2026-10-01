# Trigger evals

Each case checks that a realistic request makes the agent load the right skill. They run with
[`claude plugin eval`](https://code.claude.com/docs/en/plugins/plugin-evals.md), which starts a
fresh Claude Code session per run with only this repository's skills installed.

```
evals/<case>/
├── prompt.md               # the user request, plus run settings in frontmatter
└── graders/selects-skill.md  # passes when the Skill tool is called with the expected skill
```

Add at least one case per skill, written the way a scientist would actually ask, without
naming the skill. A case that names the skill tests nothing.

Run locally (calls the model, so it uses credits; capped by `--max-cost-usd`):

```bash
aiscientist-skill eval                      # all cases
aiscientist-skill eval --case 'qc-cellqc-*' # one skill
```

In CI the evals run on demand (the **Evals** workflow) or when a PR is labeled `run-evals`,
and need an `ANTHROPIC_API_KEY` repository secret.
