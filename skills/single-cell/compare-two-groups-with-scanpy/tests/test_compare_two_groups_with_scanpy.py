"""Runs scripts/reference.py on a small synthetic AnnData. Skipped where scanpy is not installed."""

import json
import runpy
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
ad = pytest.importorskip("anndata")
pytest.importorskip("scanpy")

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reference.py"
PLANTED = [f"up{i}" for i in range(5)]


def synthetic(path: Path) -> None:
    rng = np.random.default_rng(0)
    genes = PLANTED + [f"g{i}" for i in range(35)]
    x = rng.poisson(2.0, size=(120, len(genes))).astype(float)
    x[:60, : len(PLANTED)] += 12.0  # group "0" over-expresses the planted genes
    x = np.log1p(x)
    obs = pd.DataFrame({"leiden": ["0"] * 60 + ["1"] * 60}, index=[f"c{i}" for i in range(120)])
    ad.AnnData(x, obs=obs, var=pd.DataFrame(index=genes)).write_h5ad(path)


def test_two_groups_give_a_table_and_the_planted_genes(tmp_path, monkeypatch, capsys):
    work, art = tmp_path / "work", tmp_path / "results"
    work.mkdir()
    synthetic(work / "adata_qc.h5ad")
    monkeypatch.setenv("AISCIENTIST_WORK", str(work))
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(art))
    runpy.run_path(str(SCRIPT), run_name="__main__")
    summary = json.loads(capsys.readouterr().out)
    assert summary["n_cells"] == {"0": 60, "1": 60}
    assert set(PLANTED) <= set(summary["top_up"])
    assert summary["n_significant"] >= len(PLANTED)
    table = pd.read_csv(art / "tables" / "de_0_vs_1.csv")
    assert table["pvals_adj"].is_monotonic_increasing


def test_a_missing_group_column_is_named(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    synthetic(work / "adata_qc.h5ad")
    adata = ad.read_h5ad(work / "adata_qc.h5ad")
    del adata.obs["leiden"]
    adata.write_h5ad(work / "adata_qc.h5ad")
    monkeypatch.setenv("AISCIENTIST_WORK", str(work))
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(tmp_path / "results"))
    with pytest.raises(SystemExit, match="no column 'leiden'"):
        runpy.run_path(str(SCRIPT), run_name="__main__")
