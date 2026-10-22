"""Runs scripts/reference.py on a small synthetic Perturb-seq AnnData.

Skipped where scanpy is not installed; the Mixscape run itself is skipped where pertpy is not.
The screen: a non-targeting control (NT), a knockout (GENEA) where half the cells lost the target
and switched on a 5-gene program while the other half escaped and look like control, and a
silent guide (GENEB).
"""

import json
import runpy
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
ad = pytest.importorskip("anndata")
pytest.importorskip("scanpy")

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reference.py"
PROGRAM = [f"prog{i}" for i in range(5)]
N_CONTROL, N_KO, N_ESCAPED, N_SILENT = 100, 40, 40, 60


def synthetic(seed: int = 0):
    """log1p counts; every gene has a Poisson(4) baseline, effects are planted per cell."""
    rng = np.random.default_rng(seed)
    genes = ["GENEA", "GENEB", *PROGRAM] + [f"g{i}" for i in range(40)]
    labels = ["NT"] * N_CONTROL + ["GENEA"] * (N_KO + N_ESCAPED) + ["GENEB"] * N_SILENT
    knocked_out = np.zeros(len(labels), dtype=bool)
    knocked_out[N_CONTROL : N_CONTROL + N_KO] = True  # the first GENEA cells; the rest escaped
    counts = rng.poisson(4.0, size=(len(labels), len(genes))).astype(float)
    counts[knocked_out, 0] = rng.poisson(0.2, size=knocked_out.sum())
    counts[np.ix_(knocked_out, [2, 3, 4, 5, 6])] += rng.poisson(20.0, size=(N_KO, len(PROGRAM)))
    obs = pd.DataFrame(
        {"perturbation": labels, "planted_ko": knocked_out},
        index=[f"c{i}" for i in range(len(labels))],
    )
    return ad.AnnData(np.log1p(counts), obs=obs, var=pd.DataFrame(index=genes))


def setup(tmp_path, monkeypatch, adata) -> Path:
    work = tmp_path / "work"
    work.mkdir()
    adata.write_h5ad(work / "adata_qc.h5ad")
    monkeypatch.setenv("AISCIENTIST_WORK", str(work))
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(tmp_path / "results"))
    return work


def test_escaped_cells_are_labelled_and_removed(tmp_path, monkeypatch, capsys):
    pytest.importorskip("pertpy")
    work = setup(tmp_path, monkeypatch, synthetic())
    runpy.run_path(str(SCRIPT), run_name="__main__")
    summary = json.loads(capsys.readouterr().out)

    assert summary["mixscape"] == "OK"
    assert summary["n_cells_before"] == N_CONTROL + N_KO + N_ESCAPED + N_SILENT
    assert summary["np_fraction_by_perturbation"]["GENEA"] == pytest.approx(0.5, abs=0.1)
    # A guide without enough DE genes against control is labelled NP as a whole: a silent guide
    # loses every cell here, which is what "no detectable signature" looks like in Mixscape.
    assert summary["np_fraction_by_perturbation"]["GENEB"] == 1.0

    kept = ad.read_h5ad(work / "adata_mixscape.h5ad").obs
    assert len(kept) == summary["n_cells_after_removing_NP"]
    assert (kept["perturbation"] == "NT").sum() == N_CONTROL  # the control is never filtered
    assert (kept["perturbation"] == "GENEB").sum() == 0
    genea = kept[kept["perturbation"] == "GENEA"]
    assert set(genea["mixscape_class_global"]) == {"KO"}
    assert genea["planted_ko"].mean() >= 0.9  # what is kept are the cells that lost the target
    assert len(genea) >= 0.8 * N_KO


def test_without_pertpy_the_step_is_skipped_and_says_so(tmp_path, monkeypatch, capsys):
    work = setup(tmp_path, monkeypatch, synthetic())
    monkeypatch.setitem(sys.modules, "pertpy", None)  # import pertpy now raises ImportError
    with pytest.raises(SystemExit) as stop:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert stop.value.code == 0  # skipping never blocks the analysis
    summary = json.loads(capsys.readouterr().out)
    assert summary["mixscape"] == "SKIPPED"
    assert "ALL guide-assigned cells" in summary["consequence"]
    assert not (work / "adata_mixscape.h5ad").exists()


def test_a_missing_perturbation_column_is_named(tmp_path, monkeypatch):
    adata = synthetic()
    adata.obs = adata.obs.rename(columns={"perturbation": "guide"})
    setup(tmp_path, monkeypatch, adata)
    with pytest.raises(SystemExit, match="no column 'perturbation'"):
        runpy.run_path(str(SCRIPT), run_name="__main__")
