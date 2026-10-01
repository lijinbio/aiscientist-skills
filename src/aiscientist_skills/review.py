"""Permission review: what a change asks for beyond the baseline.

Baseline: no secrets, no runtime network access, no allowed-tools grant and no executable
code. Anything beyond that, added or widened relative to the base ref, needs a security review.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .registry import NETWORK_LEVELS


def base_catalog(root: Path, base: str) -> dict:
    try:
        out = subprocess.run(
            ["git", "show", f"{base}:catalog.json"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError:
        return {"skills": []}  # catalog.json did not exist at base
    return json.loads(out)


def changed_code(root: Path, base: str) -> set[str]:
    """Skill paths whose scripts/ changed since the merge base."""
    out = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD", "--", "skills/*/*/scripts/**"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {"/".join(p.split("/")[:3]) for p in out.splitlines() if p}


def escalations(old: dict | None, new: dict) -> list[str]:
    o = old["requirements"] if old else {"network": "none", "secrets": [], "allowed_tools": ""}
    n = new["requirements"]
    found = []
    if NETWORK_LEVELS.index(n["network"]) > max(
        NETWORK_LEVELS.index(o["network"]), NETWORK_LEVELS.index("install")
    ):
        found.append(f"network access at runtime (was `{o['network']}`)")
    if added := sorted(set(n["secrets"]) - set(o["secrets"])):
        found.append(f"new secrets: {', '.join(f'`{s}`' for s in added)}")
    if n["allowed_tools"] and n["allowed_tools"] != o["allowed_tools"]:
        found.append(f"allowed-tools set to `{n['allowed_tools']}`")
    if n["gpu"] and not (old and o.get("gpu")):
        found.append("requires a GPU")
    return found


def review(root: Path, base: str, current: dict) -> tuple[bool, str]:
    old = {s["path"]: s for s in base_catalog(root, base)["skills"]}
    code = changed_code(root, base)
    rows = []
    for s in current["skills"]:
        items = escalations(old.get(s["path"]), s)
        if s["path"] in code:
            items.append("executable code in `scripts/` changed")
        if old.get(s["path"]) and old[s["path"]]["status"] != s["status"]:
            items.append(f"status `{old[s['path']]['status']}` → `{s['status']}`")
        rows += [f"| `{s['path']}` | {i} |" for i in items]

    if not rows:
        return False, "### Permission review\n\nNo permissions beyond the baseline. ✅\n"
    table = "\n".join(["| Skill | Needs review |", "| --- | --- |", *rows])
    return (
        True,
        f"### Permission review\n\nThis change asks for more than the baseline.\n\n{table}\n",
    )
