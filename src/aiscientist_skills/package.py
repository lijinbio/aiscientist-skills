"""Release packaging: one zip per skill (uploadable to the Claude apps) plus catalog.json."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from .registry import Skill

EXCLUDE = {"__pycache__", ".DS_Store", ".pytest_cache"}
EPOCH = (1980, 1, 1, 0, 0, 0)  # fixed timestamp so identical inputs give identical zips


def zip_skill(skill: Skill, out: Path) -> Path:
    dest = out / f"{skill.name}-{skill.version}.zip"
    paths = sorted(
        p
        for p in skill.dir.rglob("*")
        if p.is_file() and not EXCLUDE.intersection(p.relative_to(skill.dir).parts)
    )
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            info = zipfile.ZipInfo(f"{skill.name}/{p.relative_to(skill.dir).as_posix()}", EPOCH)
            info.external_attr = (p.stat().st_mode & 0o777) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, p.read_bytes())
    return dest


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package(skills: list[Skill], catalog: dict, out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    zips = [zip_skill(s, out) for s in skills]
    (out / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    (out / "SHA256SUMS").write_text(
        "".join(f"{sha256(p)}  {p.name}\n" for p in [*zips, out / "catalog.json"]),
        encoding="utf-8",
    )
    return zips
