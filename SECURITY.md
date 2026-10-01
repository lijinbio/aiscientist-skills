# Security policy

## Reporting a vulnerability

Please don't open a public issue. Use GitHub's
[private vulnerability reporting](https://github.com/lijinbio/aiscientist-skills/security/advisories/new)
instead. We aim to respond within five working days.

Report, for example:

- a skill whose instructions or `scripts/` would exfiltrate data, run untrusted code, or reach
  hosts its frontmatter doesn't declare;
- a leaked credential, personal path or private dataset reference;
- a way around the validation or permission-review gates.

## What the registry guarantees

Every merged skill has passed schema validation, content checks for leaked paths, accounts and
tokens, and the permission review described in [docs/governance.md](docs/governance.md). Skills
are instructions an agent follows. Review a skill before you run it on sensitive data, and run
`community` skills with the same care as any unreviewed code.
