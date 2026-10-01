"""Scaffold a new skill from template/."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def new_skill(root: Path, spec: str, author: str = "") -> Path:
    """Create skills/<category>/<name>/ from template/ and fill in the identifiers."""
    category, sep, name = spec.partition("/")
    if not sep or not NAME_RE.match(category) or not NAME_RE.match(name) or len(name) > 64:
        raise SystemExit("usage: new <category>/<skill-name> (lowercase letters, digits, hyphens)")
    dest = root / "skills" / category / name
    if dest.exists():
        raise SystemExit(f"{dest.relative_to(root)} already exists")

    shutil.copytree(root / "template", dest)
    skill_md = dest / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    text = text.replace("name: verb-object-with-tool", f"name: {name}", 1)
    text = text.replace("category: category-name", f"category: {category}", 1)
    if author:
        text = text.replace('author: ""', f'author: "{author}"', 1)
    skill_md.write_text(text, encoding="utf-8")
    return dest
