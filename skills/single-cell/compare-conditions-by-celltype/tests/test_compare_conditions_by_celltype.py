"""Runs scripts/reference.py on a small synthetic KO-vs-WT object. Skipped without scanpy.

Three cell types (Rod, Cone, MG) of 40 KO + 40 WT cells each, and a rare type (RPE, 10 + 10
cells) that must be skipped. Two genes go up and two go down in KO in Rod and Cone (a shared
signature); one more goes up in KO only in MG.
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
SHARED_UP, SHARED_DOWN, MG_ONLY = ["UP1", "UP2"], ["DN1", "DN2"], "MGUP"


def synthetic() -> "ad.AnnData":
    rng = np.random.default_rng(0)
    genes = [*SHARED_UP, *SHARED_DOWN, MG_ONLY] + [f"g{i}" for i in range(45)]
    sizes = {"Rod": 40, "Cone": 40, "MG": 40, "RPE": 10}
    cond, ctype = [], []
    for ct, n in sizes.items():
        for c in ("KO", "WT"):
            cond += [c] * n
            ctype += [ct] * n
    cond, ctype = np.array(cond), np.array(ctype)
    x = rng.poisson(3.0, size=(len(cond), len(genes))).astype(float)
    photoreceptor_ko = (cond == "KO") & np.isin(ctype, ["Rod", "Cone"])
    photoreceptor_wt = (cond == "WT") & np.isin(ctype, ["Rod", "Cone"])
    for g in SHARED_UP:
        x[photoreceptor_ko, genes.index(g)] += 15.0
    for g in SHARED_DOWN:
        x[photoreceptor_wt, genes.index(g)] += 15.0
    x[(cond == "KO") & (ctype == "MG"), genes.index(MG_ONLY)] += 15.0
    obs = pd.DataFrame(
        {"sampleid": cond, "majorclass": pd.Categorical(ctype)},
        index=[f"c{i}" for i in range(len(cond))],
    )
    return ad.AnnData(np.log1p(x), obs=obs, var=pd.DataFrame(index=genes))


def run(tmp_path: Path, monkeypatch, adata: "ad.AnnData", capsys) -> tuple[dict, Path]:
    work, art = tmp_path / "work", tmp_path / "results"
    work.mkdir()
    adata.write_h5ad(work / "adata_qc.h5ad")
    monkeypatch.setenv("AISCIENTIST_WORK", str(work))
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(art))
    runpy.run_path(str(SCRIPT), run_name="__main__")
    return json.loads(capsys.readouterr().out), art


def test_per_celltype_tables_shared_signature_and_handoff(tmp_path, monkeypatch, capsys):
    summary, art = run(tmp_path, monkeypatch, synthetic(), capsys)
    per = {r["celltype"]: r for r in summary["per_celltype"]}
    assert per["RPE"]["skipped"] == "too_few_cells"
    assert per["RPE"]["n_condition"] == 10
    for ct in ("Rod", "Cone"):
        assert per[ct]["skipped"] == ""
        assert per[ct]["n_up"] >= 2
        assert per[ct]["n_down"] >= 2
        assert (art / "tables" / "DEG" / f"DEG_{ct}.csv").exists()
        assert (art / "figures" / "DEG" / f"volcano_{ct}.png").stat().st_size > 0
    assert not (art / "tables" / "DEG" / "DEG_RPE.csv").exists()

    # Changed in the same direction in >= 2 cell types; the MG-only gene is not shared.
    assert set(SHARED_UP) <= set(summary["shared_up_top"])
    assert set(SHARED_DOWN) <= set(summary["shared_down_top"])
    assert MG_ONLY not in summary["shared_up_top"]
    shared_up = pd.read_csv(art / "tables" / "shared_up_DEGs.csv")["gene"]
    assert set(SHARED_UP) <= set(shared_up)

    # The hand-off table carries BOTH directions, grouped by cell type, with every tested gene in
    # the universe file.
    handoff = pd.read_csv(art / "tables" / "de_majorclass_all.csv")
    assert list(handoff.columns) == ["group", "gene", "log2fc", "pval", "pval_adj", "score"]
    rod = handoff[handoff["group"] == "Rod"].set_index("gene")
    assert (rod.loc[SHARED_UP, "log2fc"] > 0).all()
    assert (rod.loc[SHARED_DOWN, "log2fc"] < 0).all()
    assert "RPE" not in set(handoff["group"])
    universe = (art / "tables" / "de_majorclass_universe.txt").read_text().split()
    assert len(universe) == 50
    assert (art / "tables" / "DEG_summary.csv").exists()


def test_the_raw_dataset_is_used_when_there_is_no_qc_checkpoint(tmp_path, monkeypatch, capsys):
    dataset = tmp_path / "input.h5ad"
    synthetic().write_h5ad(dataset)
    work, art = tmp_path / "work", tmp_path / "results"
    work.mkdir()
    monkeypatch.setenv("AISCIENTIST_WORK", str(work))
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(art))
    monkeypatch.setenv("AISCIENTIST_DATASET", str(dataset))
    runpy.run_path(str(SCRIPT), run_name="__main__")
    summary = json.loads(capsys.readouterr().out)
    assert summary["de_table"] == "tables/de_majorclass_all.csv"


def test_a_missing_level_is_named(tmp_path, monkeypatch, capsys):
    adata = synthetic()
    adata.obs["sampleid"] = adata.obs["sampleid"].replace({"KO": "HET"})
    with pytest.raises(SystemExit, match=r"'KO'/'WT' not in sampleid values \['HET', 'WT'\]"):
        run(tmp_path, monkeypatch, adata, capsys)


def test_a_missing_column_is_named(tmp_path, monkeypatch, capsys):
    adata = synthetic()
    del adata.obs["majorclass"]
    with pytest.raises(SystemExit, match="no column 'majorclass'"):
        run(tmp_path, monkeypatch, adata, capsys)
