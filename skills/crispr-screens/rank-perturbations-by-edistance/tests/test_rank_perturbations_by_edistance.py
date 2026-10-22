"""Runs scripts/reference.py on a small synthetic Perturb-seq AnnData.

Skipped where scanpy is not installed. The screen: a non-targeting control (NT), two guides that
switch on the same 5-gene program (GENEA, GENED), a silent guide (GENEB) and a guide with too few
cells (GENEC).
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
SCREEN = {"NT": 80, "GENEA": 60, "GENEB": 60, "GENEC": 10, "GENED": 60}


def synthetic(groups: dict[str, int], seed: int = 0):
    """log1p counts; every gene has a Poisson(4) baseline, GENEA and GENED switch on PROGRAM."""
    rng = np.random.default_rng(seed)
    genes = PROGRAM + [f"g{i}" for i in range(55)]
    labels = [label for label, n in groups.items() for _ in range(n)]
    counts = rng.poisson(4.0, size=(len(labels), len(genes))).astype(float)
    for i, label in enumerate(labels):
        if label in ("GENEA", "GENED"):
            counts[i, : len(PROGRAM)] += rng.poisson(20.0, size=len(PROGRAM))
    obs = pd.DataFrame({"perturbation": labels}, index=[f"c{i}" for i in range(len(labels))])
    return ad.AnnData(np.log1p(counts), obs=obs, var=pd.DataFrame(index=genes))


def adapted(tmp_path, old: str, new: str) -> Path:
    """A copy of the script with one CONFIG line changed, as a user adapts it."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert old in text
    path = tmp_path / "reference_adapted.py"
    path.write_text(text.replace(old, new), encoding="utf-8")
    return path


def run(tmp_path, monkeypatch, capsys, adata, name="adata_qc.h5ad", script=SCRIPT):
    work, art = tmp_path / "work", tmp_path / "results"
    work.mkdir(exist_ok=True)
    adata.write_h5ad(work / name)
    monkeypatch.setenv("AISCIENTIST_WORK", str(work))
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(art))
    runpy.run_path(str(script), run_name="__main__")
    return json.loads(capsys.readouterr().out), art / "tables"


def test_perturbations_with_an_effect_rank_first_and_silent_ones_are_not_called(
    tmp_path, monkeypatch, capsys
):
    summary, tables = run(tmp_path, monkeypatch, capsys, synthetic(SCREEN))

    assert summary["n_perturbations"] == 4
    assert summary["n_tested"] == 3
    assert summary["n_skipped_low_cells"] == 1
    assert summary["n_significant"] == 2
    assert sorted(summary["real_hits_for_DE"]) == ["GENEA", "GENED"]

    table = pd.read_csv(tables / "perturbation_edistance.csv")
    assert table["edistance"].is_monotonic_decreasing
    assert set(table["perturbation"].head(2)) == {"GENEA", "GENED"}
    row = table.set_index("perturbation")
    assert not row.loc["GENEB", "significant"]
    assert row.loc["GENEB", "perm_padj"] > 0.05
    assert row.loc["GENEA", "perm_pvalue"] == pytest.approx(1 / 1001)  # never beaten in 1000
    assert "GENEC" not in set(table["perturbation"])  # too few cells: counted, not tested


def test_the_closed_form_equals_the_pairwise_definition(tmp_path, monkeypatch, capsys):
    """2 mean d(p,c) - mean d(p,p') - mean d(c,c'), d squared Euclidean, self-pairs included."""
    adata = synthetic(SCREEN)
    rng = np.random.default_rng(1)
    pcs = rng.normal(size=(adata.n_obs, 30))
    pcs[adata.obs["perturbation"] == "GENEA", :3] += 2.0
    adata.obsm["X_pca"] = pcs  # a clustered checkpoint already carries X_pca: it is used as is

    summary, tables = run(tmp_path, monkeypatch, capsys, adata, name="adata_clustered.h5ad")

    def sqdist(a, b):
        return ((a[:, None, :] - b[None, :, :]) ** 2).sum(-1).mean()

    labels = adata.obs["perturbation"].to_numpy()
    c = pcs[labels == "NT"]
    table = pd.read_csv(tables / "perturbation_edistance.csv").set_index("perturbation")
    for pert in ("GENEA", "GENEB", "GENED"):
        p = pcs[labels == pert]
        expected = 2 * sqdist(p, c) - sqdist(p, p) - sqdist(c, c)
        assert table.loc[pert, "edistance"] == pytest.approx(expected, rel=1e-9)
    assert summary["real_hits_for_DE"] == ["GENEA"]  # in these PCs only GENEA was shifted


def test_a_small_silent_guide_sits_higher_on_distance_but_is_not_called(
    tmp_path, monkeypatch, capsys
):
    """With no effect, E is about 2 x total variance x (1/n_P + 1/n_C): small groups rank higher."""
    adata = synthetic({"NT": 80, "SMALL": 30, "LARGE": 300, "GENEA": 60})
    summary, tables = run(tmp_path, monkeypatch, capsys, adata)
    table = pd.read_csv(tables / "perturbation_edistance.csv").set_index("perturbation")
    assert table.loc["SMALL", "edistance"] > table.loc["LARGE", "edistance"]
    assert not table.loc["SMALL", "significant"]
    assert not table.loc["LARGE", "significant"]
    assert summary["real_hits_for_DE"] == ["GENEA"]


def test_the_pairwise_matrix_groups_perturbations_that_act_alike(tmp_path, monkeypatch, capsys):
    script = adapted(tmp_path, "PAIRWISE = False", "PAIRWISE = True")
    summary, tables = run(tmp_path, monkeypatch, capsys, synthetic(SCREEN), script=script)

    matrix = pd.read_csv(tables / "perturbation_edistance_pairwise.csv", index_col=0)
    assert summary["pairwise_matrix"].endswith("perturbation_edistance_pairwise.csv")
    assert list(matrix.index) == ["GENEA", "GENEB", "GENED"]  # GENEC: too few cells
    assert np.allclose(matrix.to_numpy(), matrix.to_numpy().T)
    assert matrix.loc["GENEA", "GENED"] < matrix.loc["GENEA", "GENEB"]


def test_without_permutations_every_tested_perturbation_is_a_hit(tmp_path, monkeypatch, capsys):
    script = adapted(tmp_path, "N_PERM = 1000", "N_PERM = 0")
    summary, _ = run(tmp_path, monkeypatch, capsys, synthetic(SCREEN), script=script)
    assert summary["n_significant"] is None
    assert summary["real_hits_for_DE"][-1] == "GENEB"  # ranked by distance only, nothing called
    assert len(summary["real_hits_for_DE"]) == 3


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
