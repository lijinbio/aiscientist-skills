"""Runs scripts/reference.py on a small synthetic annotation table. Pure standard library."""

import csv
import json
import runpy
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reference.py"
COLUMNS = [
    "location", "allele", "gene_symbol", "gene_id", "consequence", "impact", "amino_acids",
    "sift", "polyphen", "max_af", "rsid", "clinical_significance",
    "cadd_phred", "revel", "alphamissense",
]  # fmt: skip

# Gene symbols are labels for the test cases, not real variants.
ROWS = [
    # ClinVar is used verbatim, whatever the rest of the row says.
    {"gene_symbol": "CV_PATH", "consequence": "stop_gained", "impact": "HIGH",
     "clinical_significance": "pathogenic"},
    {"gene_symbol": "CV_LP", "consequence": "missense_variant", "impact": "MODERATE",
     "clinical_significance": "likely_pathogenic"},
    {"gene_symbol": "CV_BENIGN", "consequence": "missense_variant", "impact": "MODERATE",
     "max_af": "0.3", "clinical_significance": "benign"},
    # Conflicting ClinVar is not upgraded: it falls through to the computed band.
    {"gene_symbol": "CONFLICT", "consequence": "missense_variant", "impact": "MODERATE",
     "max_af": "0.00001", "cadd_phred": "25", "alphamissense": "0.9",
     "clinical_significance": "conflicting_interpretations_of_pathogenicity"},
    # Rare + two predictor hits, or rare + LoF: favour pathogenic, still a VUS.
    {"gene_symbol": "TWO_PRED", "consequence": "missense_variant", "impact": "MODERATE",
     "sift": "deleterious", "polyphen": "probably_damaging", "max_af": "0.00001"},
    {"gene_symbol": "LOF", "consequence": "frameshift_variant", "impact": "HIGH", "max_af": ""},
    # Rare + one predictor hit; rare with none.
    {"gene_symbol": "ONE_PRED", "consequence": "missense_variant", "impact": "MODERATE",
     "revel": "0.8", "max_af": "0.00002"},
    {"gene_symbol": "RARE_ONLY", "consequence": "missense_variant", "impact": "MODERATE",
     "sift": "tolerated", "polyphen": "benign", "max_af": "0.00003",
     "clinical_significance": "uncertain_significance"},
    # Between the dominant cutoff (1e-4) and BA1 (0.05); above BA1.
    {"gene_symbol": "LOW_FREQ", "consequence": "missense_variant", "impact": "MODERATE",
     "max_af": "0.001"},
    {"gene_symbol": "COMMON", "consequence": "intron_variant", "impact": "MODIFIER",
     "max_af": "0.5"},
]  # fmt: skip


def write_table(art: Path, rows: list[dict]) -> None:
    (art / "tables").mkdir(parents=True)
    with (art / "tables" / "variant_annotation.tsv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, delimiter="\t")
        w.writeheader()
        for i, r in enumerate(rows):
            w.writerow({c: r.get(c, "") for c in COLUMNS} | {"location": f"1:{100 * (i + 1)}"})


def run(art: Path, monkeypatch, model: str) -> tuple[list[dict], dict]:
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(art))
    monkeypatch.setenv("AISCIENTIST_DISEASE_MODEL", model)
    runpy.run_path(str(SCRIPT), run_name="__main__")
    with (art / "tables" / "prioritized_variants.csv").open(encoding="utf-8") as fh:
        table = list(csv.DictReader(fh))
    summary = json.loads((art / "data" / "prioritization_summary.json").read_text())
    return table, summary


def test_tiers_follow_clinvar_then_frequency_then_predictors(tmp_path, monkeypatch):
    write_table(tmp_path, ROWS)
    table, summary = run(tmp_path, monkeypatch, "dominant")
    tiers = {r["Gene"]: r["Tier"] for r in table}
    assert tiers == {
        "CV_PATH": "PATHOGENIC_CLINVAR",
        "CV_LP": "LIKELY_PATHOGENIC_CLINVAR",
        "CV_BENIGN": "BENIGN_CLINVAR",
        "CONFLICT": "VUS_FAVOR_PATH",
        "TWO_PRED": "VUS_FAVOR_PATH",
        "LOF": "VUS_FAVOR_PATH",
        "ONE_PRED": "VUS_ELEVATED",
        "RARE_ONLY": "VUS",
        "LOW_FREQ": "VUS_LIKELY_BENIGN",
        "COMMON": "LIKELY_BENIGN_COMMON",
    }
    # Rows are sorted from the most to the least actionable tier.
    order = [r["Tier"] for r in table]
    assert order[:2] == ["PATHOGENIC_CLINVAR", "LIKELY_PATHOGENIC_CLINVAR"]
    assert order[-1] == "BENIGN_CLINVAR"
    evidence = {r["Gene"]: r["Evidence"] for r in table}
    assert (
        "CADD>=20.0" in evidence["CONFLICT"] and "AlphaMissense_pathogenic" in evidence["CONFLICT"]
    )
    assert "REVEL>0.5" in evidence["ONE_PRED"]
    assert "LoF/HIGH-impact" in evidence["LOF"]
    assert summary["total_variants"] == len(ROWS)
    assert summary["rare_af_cutoff"] == 1e-4
    assert summary["tier_counts"]["VUS_FAVOR_PATH"] == 3
    assert "NOT a clinical ACMG/AMP diagnosis" in summary["caveat"]


def test_the_recessive_model_raises_the_rare_cutoff(tmp_path, monkeypatch):
    write_table(tmp_path, ROWS)
    table, summary = run(tmp_path, monkeypatch, "recessive")
    tiers = {r["Gene"]: r["Tier"] for r in table}
    assert summary["rare_af_cutoff"] == 1e-2
    assert tiers["LOW_FREQ"] == "VUS"  # AF 0.001 is rare under the recessive cutoff
    assert tiers["COMMON"] == "LIKELY_BENIGN_COMMON"  # BA1 does not depend on the model


def test_a_missing_table_is_named(tmp_path, monkeypatch):
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(tmp_path))
    with pytest.raises(SystemExit, match=r"variant_annotation\.tsv not found"):
        runpy.run_path(str(SCRIPT), run_name="__main__")


def test_an_empty_table_is_refused(tmp_path, monkeypatch):
    write_table(tmp_path, [])
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(tmp_path))
    with pytest.raises(SystemExit, match="has no annotated variants"):
        runpy.run_path(str(SCRIPT), run_name="__main__")
