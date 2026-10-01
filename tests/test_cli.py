"""Tests for the registry tooling, run against a throwaway copy of the repository."""

from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from aiscientist_skills.cli import main
from aiscientist_skills.registry import load_skills
from aiscientist_skills.review import escalations

ROOT = Path(__file__).resolve().parent.parent
SKILL = "skills/single-cell/qc-snrna-with-cellqc-standalone/SKILL.md"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    dest = tmp_path / "repo"
    shutil.copytree(
        ROOT,
        dest,
        ignore=shutil.ignore_patterns(
            ".git", ".venv", "dist", "_site", "__pycache__", "*.egg-info"
        ),
    )
    return dest


def run(repo: Path, *args: str) -> int:
    return main(["-C", str(repo), *args])


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert old in text, f"{old!r} not in {path}"
    path.write_text(text.replace(old, new, 1))


def test_repository_is_valid():
    assert main(["-C", str(ROOT), "validate"]) == 0


def test_new_skill_scaffolds_and_validates(repo: Path, capsys):
    assert run(repo, "new", "single-cell/demo-skill", "--author", "Test Author") == 0
    md = (repo / "skills/single-cell/demo-skill/SKILL.md").read_text()
    assert "name: demo-skill" in md and "category: single-cell" in md
    assert 'author: "Test Author"' in md
    assert run(repo, "validate") == 1  # catalog not synced yet
    assert run(repo, "sync") == 0
    assert run(repo, "validate") == 0
    assert "demo-skill" in (repo / "README.md").read_text()
    assert (
        "./skills/single-cell/demo-skill" in (repo / ".claude-plugin/marketplace.json").read_text()
    )
    assert "no trigger eval" in capsys.readouterr().err


def test_new_rejects_bad_names(repo: Path):
    for spec in [
        "no-category",
        "single-cell/Bad_Name",
        "single-cell/qc-snrna-with-cellqc-standalone",
    ]:
        with pytest.raises(SystemExit):
            run(repo, "new", spec)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("status: core", "status: gold", "is not one of"),
        ('version: "1.0.0"', 'version: "1.0"', "does not match"),
        ("name: qc-snrna-with-cellqc-standalone", "name: other-name", "must match the directory"),
        ("category: single-cell", "category: genomics", "must match the directory"),
        ('requires-gpu: "false"', "requires-gpu: false", "is not of type 'string'"),
        ("license: MIT\n", "license: MIT\nversion: 2\n", "Additional properties"),
        ("# QC snRNA-seq", "#SBATCH --account=mylab_lab\n# QC snRNA-seq", "real Slurm account"),
        ("# QC snRNA-seq", "/Users/alice/data\n# QC snRNA-seq", "personal home path"),
        (
            "# QC snRNA-seq",
            "See [refs](references/missing.md)\n# QC snRNA-seq",
            "broken relative link",
        ),
    ],
)
def test_validate_catches(repo: Path, capsys, old: str, new: str, message: str):
    edit(repo / SKILL, old, new)
    run(repo, "sync")
    assert run(repo, "validate") == 1
    assert message in capsys.readouterr().err


def test_category_needs_plugin_entry(repo: Path, capsys):
    src = repo / "skills/single-cell/qc-snrna-with-cellqc-standalone"
    dest = repo / "skills/genomics/qc-snrna-with-cellqc-standalone"
    dest.parent.mkdir()
    shutil.move(src, dest)
    edit(dest / "SKILL.md", "category: single-cell", "category: genomics")
    assert run(repo, "validate") == 1
    assert "has no plugin entry" in capsys.readouterr().err


def test_package_is_reproducible(repo: Path, tmp_path: Path):
    out1, out2 = tmp_path / "a", tmp_path / "b"
    assert run(repo, "package", "--out", str(out1)) == 0
    assert run(repo, "package", "--out", str(out2)) == 0
    z = out1 / "qc-snrna-with-cellqc-standalone-1.0.0.zip"
    assert z.read_bytes() == (out2 / z.name).read_bytes()
    assert "qc-snrna-with-cellqc-standalone/SKILL.md" in zipfile.ZipFile(z).namelist()
    assert z.name in (out1 / "SHA256SUMS").read_text()
    catalog = json.loads((out1 / "catalog.json").read_text())
    assert catalog["skills"][0]["status"] == "core"


def test_site_builds(repo: Path, tmp_path: Path):
    assert run(repo, "site", "--out", str(tmp_path / "site")) == 0
    page = (tmp_path / "site/index.html").read_text()
    assert "qc-snrna-with-cellqc-standalone" in page and "<\\/" not in page.split("<script>")[0]
    assert "/plugin marketplace add lijinbio/aiscientist-skills" in page
    assert 'MARKET = "aiscientist-skills"' in page  # `/plugin install <plugin>@<marketplace>`


def test_escalations():
    base = {
        "requirements": {"network": "install", "secrets": [], "allowed_tools": "", "gpu": False}
    }
    same = json.loads(json.dumps(base))
    assert escalations(base, same) == []
    assert escalations(None, same) == []  # a new skill at baseline needs no review
    wider = {
        "requirements": {
            "network": "runtime",
            "secrets": ["NCBI_API_KEY"],
            "allowed_tools": "Bash(curl:*)",
            "gpu": True,
        }
    }
    found = " ".join(escalations(base, wider))
    for word in ["runtime", "NCBI_API_KEY", "allowed-tools", "GPU"]:
        assert word in found


def test_review_against_git_base(repo: Path, capsys):
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run([*git, "add", "-A"], cwd=repo, check=True)
    subprocess.run([*git, "commit", "-qm", "base"], cwd=repo, check=True)
    edit(repo / SKILL, 'requires-secrets: "none"', 'requires-secrets: "NCBI_API_KEY"')
    run(repo, "sync")
    subprocess.run([*git, "commit", "-qam", "secret"], cwd=repo, check=True)
    assert run(repo, "review", "--base", "HEAD~1") == 0
    assert "NCBI_API_KEY" in capsys.readouterr().out


def test_records_expose_requirements():
    [skill] = load_skills(ROOT)
    req = skill.to_record()["requirements"]
    assert req == {
        "compute": skill.meta["compute"],
        "gpu": False,
        "scheduler": "optional",
        "network": "install",
        "secrets": [],
        "allowed_tools": "",
    }
