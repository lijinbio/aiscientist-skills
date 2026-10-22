"""Runs scripts/reference.py on a small synthetic mouse-style AnnData. Skipped without scanpy.

The script's default signature is written in human symbols (IFNG, STAT1, GBP1, CXCL10, IRF1);
the object uses mouse case (Ifng, Stat1, ...), keeps only "variable" genes in X and the full
log-normalised matrix in .raw, as a clustering checkpoint does. Cluster "1" over-expresses the
signature.
"""

import json
import runpy
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
ad = pytest.importorskip("anndata")
pytest.importorskip("scanpy")
pytest.importorskip("matplotlib")

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reference.py"
SIGNATURE = ["Ifng", "Stat1", "Gbp1", "Cxcl10", "Irf1"]


def synthetic(signature: list[str] = SIGNATURE, *, counts: bool = False) -> "ad.AnnData":
    rng = np.random.default_rng(0)
    genes = signature + [f"Gene{i}" for i in range(195)]
    x = rng.poisson(2.0, size=(120, len(genes))).astype(float)
    x[60:, : len(signature)] += 10.0  # cluster "1" over-expresses the signature
    if counts:
        x[0, -1] = 120.0  # integer counts beyond any log-normalised value
    else:
        x = np.log1p(x)
    obs = pd.DataFrame({"leiden": ["0"] * 60 + ["1"] * 60}, index=[f"c{i}" for i in range(120)])
    full = ad.AnnData(x, obs=obs, var=pd.DataFrame(index=genes))
    if counts:
        return full
    hvg = full[:, [f"Gene{i}" for i in range(50)]].copy()  # X: "variable" genes only
    hvg.raw = full
    return hvg


def run(tmp_path: Path, monkeypatch, adata: "ad.AnnData") -> tuple[Path, Path]:
    work, art = tmp_path / "work", tmp_path / "results"
    work.mkdir()
    adata.write_h5ad(work / "adata_clustered.h5ad")
    monkeypatch.setenv("AISCIENTIST_WORK", str(work))
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(art))
    runpy.run_path(str(SCRIPT), run_name="__main__")
    return work, art


def test_signature_is_found_in_raw_by_case_and_separates_the_groups(tmp_path, monkeypatch):
    work, art = run(tmp_path, monkeypatch, synthetic())
    report = json.loads((art / "tables" / "signature_summary.json").read_text())
    assert report["matrix"] == ".raw (all genes, log-normalised)"
    entry = report["signatures"]["interferon_response"]
    assert entry["status"] == "scored"
    assert entry["coverage"] == 1.0
    assert entry["remapped_by_case"] == {g.upper(): g for g in SIGNATURE}
    assert entry["missing"] == []

    by_group = pd.read_csv(art / "tables" / "signature_score_by_group.csv")
    means = by_group.set_index("leiden")["mean"]
    assert means.loc[1] > means.loc[0] + 1.0
    assert set(by_group.columns) >= {"signature", "n_cells", "median", "q25", "q75"}
    per_cell = pd.read_csv(art / "tables" / "signature_scores_per_cell.csv", index_col=0)
    assert len(per_cell) == 120
    assert "score_interferon_response" in ad.read_h5ad(work / "adata_scored.h5ad").obs
    assert (art / "figures" / "signature_interferon_response_by_group.png").stat().st_size > 0


def test_low_coverage_is_not_scored(tmp_path, monkeypatch, capsys):
    """Two of five genes is a different signature with the original's name on it."""
    with pytest.raises(SystemExit, match="nothing was scored"):
        run(tmp_path, monkeypatch, synthetic(["Ifng", "Stat1", "Other1", "Other2", "Other3"]))
    report = json.loads(capsys.readouterr().out)
    entry = report["signatures"]["interferon_response"]
    assert entry["status"].startswith("NOT SCORED: only 2 of 5 genes found")
    assert sorted(entry["missing"]) == ["CXCL10", "GBP1", "IRF1"]


def test_integer_counts_are_refused(tmp_path, monkeypatch):
    with pytest.raises(SystemExit, match="integer counts"):
        run(tmp_path, monkeypatch, synthetic(counts=True))
