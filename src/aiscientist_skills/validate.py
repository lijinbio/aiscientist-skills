"""Validation rules: frontmatter schema, repository structure and content hygiene."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path

from jsonschema import Draft202012Validator

from .registry import Skill

MAX_BODY_LINES = 500
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
CODE_RE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)

# Content that should never ship in a public skill. Each entry: (pattern, message).
LEAKS = [
    (re.compile(r"/(?:Users|home)/(?!user\b|username\b|you\b)[a-z][\w.-]*/"), "personal home path"),
    (re.compile(r"[\w.+-]+@[\w-]+\.(?:edu|org|com|net|io)\b"), "email address"),
    (re.compile(r"#SBATCH\s+(?:-A|--account)[= ](?!<)\S+"), "real Slurm account (use <account>)"),
    (re.compile(r"\b(?:sk-|ghp_|xox[bp]-|AKIA)[A-Za-z0-9_-]{12,}"), "credential-like token"),
]


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")


def schema_validator() -> Draft202012Validator:
    text = files("aiscientist_skills").joinpath("schemas/skill.schema.json").read_text()
    return Draft202012Validator(json.loads(text))


def check_skill(skill: Skill, validator: Draft202012Validator, report: Report) -> None:
    where = skill.path.relative_to(skill.root).as_posix()
    if skill.error:
        report.error(where, skill.error)
        return

    for err in sorted(validator.iter_errors(skill.frontmatter), key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.absolute_path) or "frontmatter"
        report.error(where, f"{loc}: {err.message}")

    if skill.frontmatter.get("name") != skill.name:
        report.error(where, f"name must match the directory name '{skill.name}'")
    if skill.meta.get("category") not in (None, skill.category):
        report.error(where, f"metadata.category must match the directory '{skill.category}'")
    if not skill.body.strip():
        report.error(where, "body is empty")
    if not re.search(r"^#{1,2} ", skill.body, re.MULTILINE):
        report.warn(where, "body has no headings")
    if (n := skill.body.count("\n")) > MAX_BODY_LINES:
        report.warn(where, f"body is {n} lines; move detail into references/")

    for target in LINK_RE.findall(CODE_RE.sub("", skill.body)):
        if re.match(r"^[a-z]+:|^#", target):
            continue
        if not (skill.dir / target.split("#", 1)[0]).exists():
            report.error(where, f"broken relative link '{target}'")

    for f in sorted(p for p in skill.dir.rglob("*") if p.is_file()):
        rel = f.relative_to(skill.root).as_posix()
        if f.stat().st_size > 1_000_000:
            report.error(rel, "file over 1 MB; keep data out of skills")
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern, what in LEAKS:
            if m := pattern.search(text):
                line = text.count("\n", 0, m.start()) + 1
                report.error(f"{rel}:{line}", f"{what}: '{m.group(0)}'")


def check_registry(skills: list[Skill], plugins: dict[str, dict], report: Report) -> None:
    seen: dict[str, str] = {}
    for s in skills:
        if s.name in seen:
            report.error(s.rel, f"skill name also used by {seen[s.name]}")
        seen[s.name] = s.rel
    for category in sorted({s.category for s in skills} - set(plugins)):
        report.error(
            ".claude-plugin/marketplace.json",
            f"category '{category}' has no plugin entry; add one with a name and description",
        )
    for name in sorted(set(plugins) - {s.category for s in skills}):
        report.warn(".claude-plugin/marketplace.json", f"plugin '{name}' has no skills")


def check_evals(skills: list[Skill], root: Path, report: Report) -> None:
    """Every skill should have at least one trigger eval naming it in a grader."""
    graders = " ".join(p.read_text(encoding="utf-8") for p in root.glob("evals/*/graders/*.md"))
    for s in skills:
        if not re.search(rf"(?<![\w-]){re.escape(s.name)}(?![\w-])", graders):
            report.warn(s.rel, "no trigger eval in evals/ (see evals/README.md)")


def validate(skills: list[Skill], plugins: dict[str, dict], root: Path) -> Report:
    report = Report()
    if not skills:
        report.error(str(root), "no skills found under skills/<category>/<name>/SKILL.md")
    validator = schema_validator()
    for s in skills:
        check_skill(s, validator, report)
    check_registry(skills, plugins, report)
    check_evals(skills, root, report)
    return report
