"""Runs scripts/reference.py on a small synthetic Perturb-seq AnnData.

Skipped where scanpy is not installed. The screen: a non-targeting control (NT), a knockout that
loses its own target and switches on a 5-gene program (GENEA), a silent guide (GENEB), a guide
with too few cells (GENEC) and a guide that switches on the same program without losing its target
(GENED, the failed positive control).
"""

import json
import runpy
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
ad = pytest.importorskip("anndata")
pytest.importorskip("scanpy")

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reference.py"
PROGRAM = [f"prog{i}" for i in range(5)]
TARGETS = ["GENEA", "GENEB", "GENEC", "GENED"]


def synthetic(groups: dict[str, int], seed: int = 0):
    """log1p counts; every gene has a Poisson(4) baseline, effects are planted per label."""
    rng = np.random.default_rng(seed)
    genes = TARGETS + PROGRAM + [f"g{i}" for i in range(40)]
    labels = [label for label, n in groups.items() for _ in range(n)]
    counts = rng.poisson(4.0, size=(len(labels), len(genes))).astype(float)
    col = {g: i for i, g in enumerate(genes)}
    prog = [col[g] for g in PROGRAM]
    for i, label in enumerate(labels):
        target = label.split("_")[0]
        if target == "GENEA":  # knockout: own target lost, program on
            counts[i, col["GENEA"]] = rng.poisson(0.2)
            counts[i, prog] += rng.poisson(20.0, size=len(prog))
        elif target == "GENED":  # program on, target untouched
            counts[i, prog] += rng.poisson(20.0, size=len(prog))
    obs = pd.DataFrame({"perturbation": labels}, index=[f"c{i}" for i in range(len(labels))])
    return ad.AnnData(np.log1p(counts), obs=obs, var=pd.DataFrame(index=genes))


SCREEN = {"NT": 80, "GENEA": 60, "GENEB": 60, "GENEC": 10, "GENED": 60}


def adapted(tmp_path, old: str, new: str) -> Path:
    """A copy of the script with one CONFIG line changed, as a user adapts it."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert old in text
    path = tmp_path / "reference_adapted.py"
    path.write_text(text.replace(old, new), encoding="utf-8")
    return path


def run(tmp_path, monkeypatch, capsys, adata, script=SCRIPT):
    work, art = tmp_path / "work", tmp_path / "results"
    work.mkdir(exist_ok=True)
    adata.write_h5ad(work / "adata_qc.h5ad")
    monkeypatch.setenv("AISCIENTIST_WORK", str(work))
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(art))
    runpy.run_path(str(script), run_name="__main__")
    return json.loads(capsys.readouterr().out), art / "tables"


def test_each_perturbation_is_compared_with_the_shared_control(tmp_path, monkeypatch, capsys):
    summary, tables = run(tmp_path, monkeypatch, capsys, synthetic(SCREEN))

    assert summary["control"] == "NT"
    assert summary["level"] == "guide"
    assert summary["n_perturbations_tested"] == 3
    assert summary["n_skipped_low_cells"] == 1
    for pert in ("GENEA", "GENEB", "GENED"):
        assert (tables / "perturbation_DE" / f"DE_{pert}.csv").is_file()
    assert not (tables / "perturbation_DE" / "DE_GENEC.csv").exists()

    table = pd.read_csv(tables / "perturbation_DE_summary.csv").set_index("perturbation")
    assert table.loc["GENEC", "skipped"] == "too_few_cells"
    assert table.loc["GENEA", "n_DEG"] >= len(PROGRAM) + 1  # the program up, the target down
    assert table.loc["GENEB", "n_DEG"] == 0  # silent guide: nothing called
    assert (table["n_control"] == 80).all()

    de = pd.read_csv(tables / "perturbation_DE" / "DE_GENEA.csv")
    assert de["pvals_adj"].is_monotonic_increasing
    assert set(PROGRAM) <= set(de.nsmallest(len(PROGRAM) + 1, "pvals_adj")["names"])


def test_self_knockdown_is_the_positive_control(tmp_path, monkeypatch, capsys):
    summary, tables = run(tmp_path, monkeypatch, capsys, synthetic(SCREEN))
    table = pd.read_csv(tables / "perturbation_DE_summary.csv").set_index("perturbation")
    assert table.loc["GENEA", "target_self_knockdown"] == "down"
    # GENED moves the program without losing its target (mislabel?); the silent GENEB guide
    # never lowered its target either (no editing?). Both fail the positive control.
    assert table.loc["GENED", "target_self_knockdown"].startswith("NOT_down")
    assert table.loc["GENEB", "target_self_knockdown"].startswith("NOT_down")
    assert summary["failed_self_knockdown_positive_control"] == ["GENEB", "GENED"]


def test_genes_shared_by_two_perturbations_are_collected(tmp_path, monkeypatch, capsys):
    summary, tables = run(tmp_path, monkeypatch, capsys, synthetic(SCREEN))
    assert set(PROGRAM) <= set(summary["shared_up_top"])
    shared = pd.read_csv(tables / "shared_up_across_perturbations.csv")["gene"]
    assert set(shared) == set(PROGRAM)
    assert summary["n_shared_down"] == 0  # GENEA is the only gene down, in one perturbation


def test_collapsing_guides_to_targets_pools_small_guides(tmp_path, monkeypatch, capsys):
    guides = {"NT": 80, "GENEA_sg1": 20, "GENEA_sg2": 20}  # each guide is under MIN_CELLS = 30
    adata = synthetic(guides)

    summary, _ = run(tmp_path, monkeypatch, capsys, adata)
    assert summary["n_perturbations_tested"] == 0
    assert summary["n_skipped_low_cells"] == 2

    script = adapted(
        tmp_path, "COLLAPSE_GUIDE_TO_TARGET = False", "COLLAPSE_GUIDE_TO_TARGET = True"
    )
    summary, _ = run(tmp_path, monkeypatch, capsys, adata, script=script)
    assert summary["level"] == "target"
    assert summary["n_perturbations_tested"] == 1
    top = summary["top_by_n_DEG"][0]
    assert (top["perturbation"], top["n_cells"]) == ("GENEA", 40)
    assert top["target_self_knockdown"] == "down"


def test_only_the_listed_hits_are_tested(tmp_path, monkeypatch, capsys):
    script = adapted(tmp_path, "ONLY_PERTURBATIONS = None", 'ONLY_PERTURBATIONS = ["GENEA"]')
    summary, tables = run(tmp_path, monkeypatch, capsys, synthetic(SCREEN), script=script)
    assert summary["n_perturbations_tested"] == 1
    assert sorted(p.name for p in (tables / "perturbation_DE").iterdir()) == ["DE_GENEA.csv"]


def test_the_raw_dataset_is_read_when_there_is_no_checkpoint(tmp_path, monkeypatch, capsys):
    dataset = tmp_path / "screen.h5ad"
    synthetic(SCREEN).write_h5ad(dataset)
    (tmp_path / "work").mkdir()
    monkeypatch.setenv("AISCIENTIST_WORK", str(tmp_path / "work"))
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(tmp_path / "results"))
    monkeypatch.setenv("AISCIENTIST_DATASET", str(dataset))
    runpy.run_path(str(SCRIPT), run_name="__main__")
    assert json.loads(capsys.readouterr().out)["n_perturbations_tested"] == 3


def test_a_missing_control_is_named(tmp_path, monkeypatch, capsys):
    adata = synthetic(SCREEN)
    adata.obs["perturbation"] = adata.obs["perturbation"].replace({"NT": "non-targeting"})
    with pytest.raises(SystemExit, match="control 'NT' not in perturbation"):
        run(tmp_path, monkeypatch, capsys, adata)


def test_a_missing_perturbation_column_is_named(tmp_path, monkeypatch, capsys):
    adata = synthetic(SCREEN)
    adata.obs = adata.obs.rename(columns={"perturbation": "guide"})
    with pytest.raises(SystemExit, match="no column 'perturbation'"):
        run(tmp_path, monkeypatch, capsys, adata)
