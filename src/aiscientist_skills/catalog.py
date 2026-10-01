"""Generated artifacts: README catalog, marketplace skill lists, catalog.json."""

from __future__ import annotations

import json
from pathlib import Path

from . import __version__
from .registry import Skill

BEGIN, END = "<!-- BEGIN SKILLS -->", "<!-- END SKILLS -->"
STATUS_BADGE = {"core": "🟢 core", "verified": "🔵 verified", "community": "⚪ community"}


def plugins_by_name(market: dict) -> dict[str, dict]:
    return {p["name"]: p for p in market.get("plugins", [])}


def render_readme_catalog(skills: list[Skill], plugins: dict[str, dict]) -> str:
    out = [BEGIN, ""]
    for category in sorted({s.category for s in skills}):
        out += [f"### {category}", ""]
        if desc := plugins.get(category, {}).get("description"):
            out += [desc, ""]
        out += ["| Skill | Status | Version | What it does |", "| --- | --- | --- | --- |"]
        for s in (s for s in skills if s.category == category):
            summary = s.summary.replace("|", "\\|")
            out.append(
                f"| [`{s.name}`]({s.rel}/) | {STATUS_BADGE.get(s.status, s.status)} "
                f"| {s.version} | {summary} |"
            )
        out.append("")
    out.append(END)
    return "\n".join(out)


def update_readme(text: str, skills: list[Skill], plugins: dict[str, dict]) -> str:
    if BEGIN not in text or END not in text:
        raise ValueError(f"README.md is missing the {BEGIN} / {END} markers")
    head, rest = text.split(BEGIN, 1)
    return head + render_readme_catalog(skills, plugins) + rest.split(END, 1)[1]


def update_marketplace(market: dict, skills: list[Skill]) -> dict:
    for name, plugin in plugins_by_name(market).items():
        plugin["skills"] = [f"./{s.rel}" for s in skills if s.category == name]
    return market


def build_catalog(skills: list[Skill], market: dict) -> dict:
    plugins = plugins_by_name(market)
    return {
        "schema_version": 1,
        "registry": market.get("name", ""),
        "registry_version": market.get("metadata", {}).get("version", ""),
        "generator": f"aiscientist-skills {__version__}",
        "categories": [
            {"name": c, "description": plugins.get(c, {}).get("description", "")}
            for c in sorted({s.category for s in skills})
        ],
        "skills": [s.to_record() for s in skills],
    }


def dumps(obj: dict) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def planned_writes(root: Path, skills: list[Skill], market: dict) -> dict[Path, str]:
    """Every generated file and the content it should have."""
    readme = root / "README.md"
    market = update_marketplace(json.loads(json.dumps(market)), skills)
    return {
        readme: update_readme(readme.read_text(encoding="utf-8"), skills, plugins_by_name(market)),
        root / ".claude-plugin" / "marketplace.json": dumps(market),
        root / "catalog.json": dumps(build_catalog(skills, market)),
    }
