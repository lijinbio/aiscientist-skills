"""Runs scripts/reference.py on small synthetic retina-like clusters. Skipped without scanpy.

Six clusters of 40 cells: rod, cone, Muller glia with a weak reactive GFAP/S100B bump (the
shared-marker trap: the z-scored first pass calls it astrocyte), microglia that also express the
Muller-panel genes APOE/CLU/SLC1A3/SOX9, a cluster with no coherent signal, and pericytes (whose
label "Pericyte/SMC" has a '/' that h5py rejects in an obs column name).
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

SPEC = {
    "0": {"RHO": 3.0, "NRL": 2.5, "GNAT1": 2.5, "PDE6A": 2.0, "PDE6B": 2.0, "NR2E3": 1.5},
    "1": {"ARR3": 3.0, "PDE6H": 2.5, "GNAT2": 2.5, "OPN1MW": 2.0, "PDE6A": 1.0},
    "2": {
        "RLBP1": 3.0,
        "GLUL": 3.0,
        "SLC1A3": 2.0,
        "CLU": 2.0,
        "APOE": 2.0,
        "SOX9": 1.0,
        "GFAP": 1.2,
        "S100B": 1.2,
        "PAX2": 0.4,
    },
    "3": {
        "C1QA": 3.0,
        "C1QB": 2.5,
        "P2RY12": 2.0,
        "CX3CR1": 2.0,
        "AIF1": 2.0,
        "APOE": 3.0,
        "CLU": 3.0,
        "SLC1A3": 2.0,
        "SOX9": 2.0,
        "GLUL": 1.0,
    },
    "4": {},
    "5": {"ACTA2": 2.0, "PDGFRB": 2.0, "NOTCH3": 2.0, "TAGLN": 2.0},
}
EXPECTED = {
    "0": "Rod photoreceptor",
    "1": "Cone photoreceptor",
    "2": "Muller glia",
    "3": "Microglia",
    "4": "Unassigned",
    "5": "Pericyte/SMC",
}


def synthetic() -> "ad.AnnData":
    """Log-normalised values: a sparse background plus each cluster's planted markers."""
    rng = np.random.default_rng(0)
    markers = sorted({g for spec in SPEC.values() for g in spec} | {"VSX2", "GRM6", "TRPM1"})
    genes = markers + [f"BG{i}" for i in range(150)]
    clusters = [c for c in SPEC for _ in range(40)]
    x = np.where(
        rng.random((len(clusters), len(genes))) < 0.2,
        rng.uniform(0.0, 1.0, (len(clusters), len(genes))),
        0.0,
    )
    for i, c in enumerate(clusters):
        for g, v in SPEC[c].items():
            x[i, genes.index(g)] = max(0.0, v + rng.normal(0, 0.2))
    obs = pd.DataFrame(
        {"leiden": pd.Categorical(clusters)}, index=[f"c{i}" for i in range(len(clusters))]
    )
    return ad.AnnData(x.astype("float32"), obs=obs, var=pd.DataFrame(index=genes))


def run(tmp_path: Path, monkeypatch, adata: "ad.AnnData") -> tuple[dict, Path, Path]:
    work, art = tmp_path / "work", tmp_path / "results"
    work.mkdir()
    adata.write_h5ad(work / "adata_de.h5ad")
    monkeypatch.setenv("AISCIENTIST_WORK", str(work))
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(art))
    runpy.run_path(str(SCRIPT), run_name="__main__")
    summary = json.loads((art / "tables" / "cluster_cell_types.json").read_text())
    return summary, work, art


def test_planted_clusters_and_the_shared_marker_correction(tmp_path, monkeypatch):
    summary, work, art = run(tmp_path, monkeypatch, synthetic())
    labels = summary["labels"]
    assert {c: v["cell_type"] for c, v in labels.items()} == EXPECTED

    # The z-scored argmax alone calls the Muller cluster an astrocyte; the raw discriminators
    # (RLBP1/GLUL vs GFAP/PAX2) overrule it, and both calls stay in the output.
    z_argmax_label = labels["2"]["first_pass_label"]
    assert z_argmax_label == "Retinal astrocyte"
    assert labels["2"]["corrected_by_raw_check"] is True
    assert labels["2"]["runner_up"] == "Retinal astrocyte"
    assert summary["corrected_by_raw_check"] == ["2"]

    # No coherent signal: left Unassigned, never forced into the nearest label.
    assert summary["unassigned"] == ["4"]
    assert labels["4"]["confidence"] == "none"
    assert labels["4"]["evidence"] == "no dominant lineage signal"

    # Lineages with no detected marker are named, not guessed.
    assert {"RPE", "Vascular endothelium", "Lymphatic endothelium"} <= set(
        summary["lineages_not_testable"]
    )
    assert "MYH11" in summary["panel_genes_absent_from_object"]["Pericyte/SMC"]

    annotated = ad.read_h5ad(work / "adata_annotated.h5ad")
    assert {"cell_type", "cluster_note"} <= set(annotated.obs.columns)
    assert not any("/" in c for c in annotated.obs.columns)
    comp = pd.read_csv(art / "tables" / "celltype_composition.csv", index_col=0)
    assert comp["n_cells"].sum() == 240
    scores = pd.read_csv(art / "tables" / "celltype_scores_by_cluster.csv", index_col=0)
    assert "Muller glia" in scores.columns


def test_markers_are_read_from_raw_when_x_holds_only_variable_genes(tmp_path, monkeypatch):
    """Clustering checkpoints keep only the highly variable genes in X; the full log-normalised
    matrix is in .raw, and scoring and the raw check must look there."""
    full = synthetic()
    hvg_only = full[:, [g.startswith("BG") for g in full.var_names]].copy()
    hvg_only.raw = full
    summary, _, _ = run(tmp_path, monkeypatch, hvg_only)
    assert {c: v["cell_type"] for c, v in summary["labels"].items()} == EXPECTED


def test_a_missing_cluster_column_is_named(tmp_path, monkeypatch):
    adata = synthetic()
    del adata.obs["leiden"]
    with pytest.raises(SystemExit, match="'leiden' not in obs"):
        run(tmp_path, monkeypatch, adata)
