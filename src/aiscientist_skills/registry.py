"""Load skills from the repository and expose them as typed records."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
STATUSES = ("core", "verified", "community")
NETWORK_LEVELS = ("none", "install", "runtime")


def find_root(start: Path | None = None) -> Path:
    """Walk up from `start` to the directory holding .claude-plugin/marketplace.json."""
    here = (start or Path.cwd()).resolve()
    for d in (here, *here.parents):
        if (d / ".claude-plugin" / "marketplace.json").is_file():
            return d
    raise SystemExit(
        "not inside an aiscientist-skills repository (no .claude-plugin/marketplace.json)"
    )


def split_list(value: str | None) -> list[str]:
    """Parse a comma-separated metadata value; 'none' and '' mean empty."""
    if not value or value.strip().lower() == "none":
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass
class Skill:
    root: Path
    path: Path  # .../skills/<category>/<name>/SKILL.md
    frontmatter: dict = field(default_factory=dict)
    body: str = ""
    error: str | None = None  # set when the file could not be parsed

    @property
    def dir(self) -> Path:
        return self.path.parent

    @property
    def rel(self) -> str:
        return self.dir.relative_to(self.root).as_posix()

    @property
    def category(self) -> str:
        return self.dir.parent.name

    @property
    def name(self) -> str:
        return self.dir.name

    @property
    def description(self) -> str:
        d = self.frontmatter.get("description")
        return d.strip() if isinstance(d, str) else ""

    @property
    def meta(self) -> dict:
        m = self.frontmatter.get("metadata")
        return m if isinstance(m, dict) else {}

    @property
    def version(self) -> str:
        return str(self.meta.get("version", "0.0.0"))

    @property
    def status(self) -> str:
        return str(self.meta.get("status", "community"))

    @property
    def tags(self) -> list[str]:
        return split_list(self.meta.get("tags"))

    @property
    def secrets(self) -> list[str]:
        return split_list(self.meta.get("requires-secrets"))

    @property
    def network(self) -> str:
        return str(self.meta.get("requires-network", "none"))

    @property
    def summary(self) -> str:
        """First sentence of the description."""
        return re.split(r"(?<=\.)\s", self.description, maxsplit=1)[0]

    @property
    def has_code(self) -> bool:
        return (self.dir / "scripts").is_dir()

    @property
    def has_tests(self) -> bool:
        return (self.dir / "tests").is_dir()

    def requirements(self) -> dict:
        """Declared runtime needs, as the app or a reviewer would read them."""
        m = self.meta
        return {
            "compute": m.get("compute", ""),
            "gpu": str(m.get("requires-gpu", "false")).lower() == "true",
            "scheduler": m.get("scheduler", "none"),
            "network": self.network,
            "secrets": self.secrets,
            "allowed_tools": self.frontmatter.get("allowed-tools", ""),
        }

    def to_record(self) -> dict:
        """Machine-readable catalog entry (catalog.json)."""
        return {
            "name": self.name,
            "category": self.category,
            "path": self.rel,
            "version": self.version,
            "status": self.status,
            "description": self.description,
            "tags": self.tags,
            "license": self.frontmatter.get("license", ""),
            "tested_with": self.meta.get("tested-with", ""),
            "author": self.meta.get("author", ""),
            "requirements": self.requirements(),
            "has_code": self.has_code,
            "has_tests": self.has_tests,
        }


def load_skill(root: Path, path: Path) -> Skill:
    skill = Skill(root=root, path=path)
    m = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    if not m:
        skill.error = "missing YAML frontmatter delimited by '---'"
        return skill
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        skill.error = f"invalid YAML frontmatter: {e}"
        return skill
    if not isinstance(fm, dict):
        skill.error = "frontmatter is not a YAML mapping"
        return skill
    skill.frontmatter, skill.body = fm, m.group(2)
    return skill


def load_skills(root: Path) -> list[Skill]:
    return [load_skill(root, p) for p in sorted((root / "skills").glob("*/*/SKILL.md"))]
