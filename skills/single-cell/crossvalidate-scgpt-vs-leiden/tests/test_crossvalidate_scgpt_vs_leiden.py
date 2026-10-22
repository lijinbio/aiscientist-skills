"""Runs scripts/reference.py on synthetic scGPT predictions and a clustered AnnData.

scGPT labels all 100 raw cells; QC kept 80 of them, in a different order, plus 5 cells scGPT never
saw. The predictions CSV is shuffled, so only a barcode join gives the planted agreement.
Skipped where scanpy is not installed.
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


def inputs(tmp_path: Path, monkeypatch, *, barcode_prefix: str = "cell") -> Path:
    rng = np.random.default_rng(0)
    work, art = tmp_path / "work", tmp_path / "results"
    (art / "data").mkdir(parents=True)
    work.mkdir()

    raw = [f"cell{i}" for i in range(100)]
    truth = ["Rod"] * 50 + ["Cone"] * 30 + ["Muller glia"] * 20
    pred_label = list(truth)
    for i in range(50, 55):  # scGPT calls 5 of the 30 cones "Rod"
        pred_label[i] = "Rod"
    confidence = [0.9] * 90 + [0.3] * 10
    pred = pd.DataFrame(
        {
            "barcode": [b.replace("cell", barcode_prefix) for b in raw],
            "predictions": pred_label,
            "confidence": confidence,
        }
    )
    pred.sample(frac=1.0, random_state=1).to_csv(
        art / "data" / "scgpt_predictions.csv", index=False
    )

    # QC drops cells 80-99 (all Muller glia); clustering adds 5 cells scGPT never labelled.
    kept = list(rng.permutation(80))
    names = [raw[i] for i in kept] + [f"extra{i}" for i in range(5)]
    leiden = ["0" if truth[i] == "Rod" else "1" for i in kept] + ["2"] * 5
    major = [truth[i].lower() for i in kept] + ["rod"] * 5
    obs = pd.DataFrame({"leiden": leiden, "majorclass": major}, index=names)
    x = rng.poisson(1.0, size=(len(names), 10)).astype("float32")
    var = pd.DataFrame(index=[f"g{i}" for i in range(10)])
    ad.AnnData(x, obs=obs, var=var).write_h5ad(work / "adata_clustered.h5ad")

    monkeypatch.setenv("AISCIENTIST_WORK", str(work))
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(art))
    return art


def test_barcode_alignment_confusion_and_purity(tmp_path, monkeypatch, capsys):
    art = inputs(tmp_path, monkeypatch)
    runpy.run_path(str(SCRIPT), run_name="__main__")
    summary = json.loads(capsys.readouterr().out)

    assert summary["cells_compared"] == 80
    assert summary["cells_scgpt_only(qc_filtered_out)"] == 20
    assert summary["cells_in_adata_without_a_prediction"] == 5
    assert set(summary["cross_validation"]) == {"leiden", "majorclass"}

    leiden = summary["cross_validation"]["leiden"]
    assert leiden["per_group"]["0"] == {"top_scgpt_label": "Rod", "purity": 1.0, "n": 50}
    assert leiden["per_group"]["1"] == {"top_scgpt_label": "Cone", "purity": 0.833, "n": 30}
    # Cluster ids never equal label strings: exact agreement is 0 and says nothing.
    assert leiden["exact_string_agreement"] == 0.0

    # Same classes, different spelling ("rod" vs "Rod"): exact agreement is rough by design.
    major = summary["cross_validation"]["majorclass"]
    assert major["per_group"]["cone"]["top_scgpt_label"] == "Cone"
    assert major["exact_string_agreement"] == 0.0

    assert summary["confidence"]["low_conf_frac(<0.5)"] == 0.0  # low-confidence cells were dropped
    confusion = pd.read_csv(art / "tables" / "scgpt_vs_leiden_confusion.csv", index_col=0)
    assert int(confusion.loc[1, "Rod"]) == 5
    assert int(confusion.to_numpy().sum()) == 80
    saved = json.loads((art / "tables" / "scgpt_crossvalidation.json").read_text())
    assert saved == summary


def test_no_shared_barcodes_stops_with_a_clear_message(tmp_path, monkeypatch):
    inputs(tmp_path, monkeypatch, barcode_prefix="AAAC-")
    with pytest.raises(SystemExit, match="No shared barcodes"):
        runpy.run_path(str(SCRIPT), run_name="__main__")
