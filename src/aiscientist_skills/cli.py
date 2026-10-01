"""aiscientist-skill: scaffold, validate, catalog, review and package skills.

Run `aiscientist-skill <command> --help` for details on each command.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from .catalog import build_catalog, planned_writes, update_marketplace
from .package import package
from .registry import find_root, load_skills
from .review import review
from .scaffold import new_skill
from .site import build_site
from .validate import validate


def _load(root: Path):
    market = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    skills = load_skills(root)
    return skills, market, {p["name"]: p for p in market.get("plugins", [])}


def _repo_url(market: dict) -> str:
    for p in market.get("plugins", []):
        if p.get("repository"):
            return p["repository"]
    return "https://github.com/lijinbio/aiscientist-skills"


def cmd_validate(args, root: Path) -> int:
    skills, market, plugins = _load(root)
    if args.only:
        wanted = {Path(p).resolve() for p in args.only}
        skills = [s for s in skills if s.dir.resolve() in wanted] or skills
    report = validate(skills, plugins, root)

    if not args.only:
        try:
            stale = [
                p.relative_to(root).as_posix()
                for p, text in planned_writes(root, skills, market).items()
                if not p.exists() or p.read_text(encoding="utf-8") != text
            ]
        except ValueError as e:
            report.errors.append(str(e))
            stale = []
        if stale:
            report.errors.append(
                f"generated files out of date: {', '.join(stale)} (run: aiscientist-skill sync)"
            )

    for w in report.warnings:
        print(f"warning: {w}", file=sys.stderr)
    for e in report.errors:
        print(f"error: {e}", file=sys.stderr)
    if report.errors:
        print(f"\n✗ {len(report.errors)} error(s)", file=sys.stderr)
        return 1
    print(f"✓ {len(skills)} skill(s) valid")
    return 0


def cmd_sync(args, root: Path) -> int:
    skills, market, _ = _load(root)
    for path, text in planned_writes(root, skills, market).items():
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            print(f"updated {path.relative_to(root)}")
    return 0


def cmd_new(args, root: Path) -> int:
    dest = new_skill(root, args.skill, author=args.author)
    print(f"created {dest.relative_to(root)}/SKILL.md")
    print("next: edit it, then run `aiscientist-skill sync && aiscientist-skill validate`")
    return 0


def cmd_list(args, root: Path) -> int:
    skills, _, _ = _load(root)
    skills = [
        s
        for s in skills
        if (not args.category or s.category == args.category)
        and (not args.status or s.status == args.status)
    ]
    if args.json:
        print(json.dumps([s.to_record() for s in skills], indent=2))
        return 0
    width = max((len(s.name) for s in skills), default=4)
    for s in skills:
        print(f"{s.name:<{width}}  {s.category:<14} {s.version:<8} {s.status:<10} {s.summary[:70]}")
    return 0


def cmd_review(args, root: Path) -> int:
    skills, market, _ = _load(root)
    catalog = build_catalog(skills, update_marketplace(market, skills))
    needs, summary = review(root, args.base, catalog)
    print(summary)
    if out := os.environ.get("GITHUB_OUTPUT"):
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"needs_review={'true' if needs else 'false'}\n")
    if summ := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summ, "a", encoding="utf-8") as f:
            f.write(summary)
    return 0


def cmd_package(args, root: Path) -> int:
    skills, market, _ = _load(root)
    out = Path(args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    zips = package(skills, build_catalog(skills, update_marketplace(market, skills)), out)
    for z in zips:
        print(f"wrote {z.relative_to(Path.cwd()) if z.is_relative_to(Path.cwd()) else z}")
    return 0


def cmd_site(args, root: Path) -> int:
    skills, market, _ = _load(root)
    catalog = build_catalog(skills, update_marketplace(market, skills))
    page = build_site(catalog, Path(args.out), _repo_url(market))
    print(f"wrote {page}")
    return 0


def cmd_test(args, root: Path) -> int:
    targets = [str(p) for p in sorted(root.glob("skills/*/*/tests"))]
    if not targets:
        print("no skill tests found (skills/<category>/<name>/tests/)")
        return 0
    return subprocess.call([sys.executable, "-m", "pytest", *targets, *args.pytest_args])


def cmd_eval(args, root: Path) -> int:
    """Thin wrapper over `claude plugin eval` with registry defaults."""
    if not shutil.which("claude"):
        print("error: the `claude` CLI is required (https://code.claude.com)", file=sys.stderr)
        return 1
    cmd = [
        "claude",
        "plugin",
        "eval",
        ".",
        "--trust-plugin",
        "--no-publish",
        "--runs",
        str(args.runs),
        "--threshold",
        str(args.threshold),
        "--max-cost-usd",
        str(args.max_cost_usd),
        "--ablation",
        "none",
    ]
    if args.case:
        cmd += ["--case", args.case]
    if args.json:
        cmd += ["--json", args.json]
    print("$ " + " ".join(cmd), file=sys.stderr)
    return subprocess.call(cmd, cwd=root)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aiscientist-skill", description=__doc__.splitlines()[0])
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("-C", "--root", help="repository root (default: search upward from cwd)")
    sub = p.add_subparsers(dest="command", required=True, metavar="<command>")

    s = sub.add_parser("new", help="scaffold a skill from template/")
    s.add_argument("skill", metavar="<category>/<skill-name>")
    s.add_argument("--author", default="", help="value for metadata.author")
    s.set_defaults(func=cmd_new)

    s = sub.add_parser("validate", aliases=["check"], help="run every CI check locally")
    s.add_argument("only", nargs="*", help="limit to these skill directories")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("sync", help="regenerate README catalog, marketplace.json, catalog.json")
    s.set_defaults(func=cmd_sync)

    s = sub.add_parser("list", help="list skills")
    s.add_argument("--category")
    s.add_argument("--status", choices=["core", "verified", "community"])
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("test", help="run each skill's tests/ with pytest")
    s.add_argument("pytest_args", nargs=argparse.REMAINDER)
    s.set_defaults(func=cmd_test)

    s = sub.add_parser("eval", help="trigger evals via `claude plugin eval` (uses model credits)")
    s.add_argument("--case", help="glob of eval case names")
    s.add_argument("--runs", type=int, default=3)
    s.add_argument("--threshold", type=float, default=0.8)
    s.add_argument("--max-cost-usd", type=float, default=5.0)
    s.add_argument("--json", help="write aggregate results to this file")
    s.set_defaults(func=cmd_eval)

    s = sub.add_parser("review", help="flag permissions requested beyond the baseline")
    s.add_argument("--base", default="origin/main", help="git ref to compare against")
    s.set_defaults(func=cmd_review)

    s = sub.add_parser("package", help="build release zips, catalog.json and SHA256SUMS")
    s.add_argument("--out", default="dist")
    s.set_defaults(func=cmd_package)

    s = sub.add_parser("site", help="build the searchable catalog page")
    s.add_argument("--out", default="_site")
    s.set_defaults(func=cmd_site)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve() if args.root else find_root()
    return args.func(args, root)


if __name__ == "__main__":
    sys.exit(main())
