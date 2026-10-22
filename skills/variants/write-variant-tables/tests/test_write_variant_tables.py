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
]  # fmt: skip
TABLES = [
    "variant_consequence_distribution.csv",
    "variant_impact_distribution.csv",
    "variant_clinical_significance.csv",
    "clinvar_pathogenic_variants.csv",
    "high_priority_variants.csv",
]

# Gene symbols are labels for the test cases, not real variants.
ROWS = [
    # rare + deleterious + not in ClinVar: high priority
    {"location": "1:100", "gene_symbol": "RARE_DEL", "consequence": "missense_variant",
     "impact": "MODERATE", "sift": "deleterious", "polyphen": "probably_damaging",
     "max_af": "0.0001", "rsid": "rs_a"},
    # in ClinVar as pathogenic: pathogenic table, not the shortlist
    {"location": "1:200", "gene_symbol": "CV_PATH", "consequence": "stop_gained", "impact": "HIGH",
     "rsid": "rs_b", "clinical_significance": "pathogenic"},
    # common: not rare, not on the shortlist
    {"location": "1:300", "gene_symbol": "COMMON", "consequence": "intron_variant",
     "impact": "MODIFIER", "max_af": "0.5", "rsid": "rs_c"},
    # HIGH impact with no frequency record (novel, counted as rare): high priority
    {"location": "1:400", "gene_symbol": "NOVEL_LOF", "consequence": "frameshift_variant",
     "impact": "HIGH", "rsid": "rs_d"},
    # in ClinVar as a VUS: rare and damaging, but not on the not-in-ClinVar shortlist
    {"location": "1:500", "gene_symbol": "CV_VUS", "consequence": "missense_variant",
     "impact": "MODERATE", "sift": "deleterious", "max_af": "0.00001", "rsid": "rs_e",
     "clinical_significance": "uncertain_significance"},
]  # fmt: skip


def write_table(art: Path, rows: list[dict]) -> None:
    (art / "tables").mkdir(parents=True)
    with (art / "tables" / "variant_annotation.tsv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, delimiter="\t")
        w.writeheader()
        w.writerows({c: r.get(c, "") for c in COLUMNS} for r in rows)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_writes_the_five_tables_and_the_summary(tmp_path, monkeypatch, capsys):
    write_table(tmp_path, ROWS)
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(tmp_path))
    runpy.run_path(str(SCRIPT), run_name="__main__")

    tables = tmp_path / "tables"
    for name in TABLES:
        assert (tables / name).exists(), f"{name} not written"

    summary = json.loads((tmp_path / "data" / "annotated_results_summary.json").read_text())
    assert summary == json.loads(capsys.readouterr().out)
    assert summary["total_variants"] == 5
    assert summary["n_pathogenic_clinvar"] == 1
    assert summary["n_rare_variants_af_lt_0.1"] == 4  # AF < 0.001, or no frequency at all
    assert summary["n_high_priority_rare_deleterious"] == 2
    assert summary["clinical_significance_distribution"] == {
        "not_in_clinvar": 3,
        "pathogenic": 1,
        "uncertain_significance": 1,
    }
    assert summary["tables_produced"] == TABLES

    shortlist = read_csv(tables / "high_priority_variants.csv")
    assert [r["Gene"] for r in shortlist] == ["RARE_DEL", "NOVEL_LOF"]
    assert all(r["ClinVar_Status"] == "not_in_clinvar" for r in shortlist)

    pathogenic = read_csv(tables / "clinvar_pathogenic_variants.csv")
    assert pathogenic == [
        {"Gene": "CV_PATH", "Position": "1:200", "rsID": "rs_b", "Disease": "pathogenic"}
    ]

    impact = {
        r["Impact"]: (r["Count"], r["Percentage"])
        for r in read_csv(tables / "variant_impact_distribution.csv")
    }
    assert impact == {
        "MODERATE": ("2", "40.00%"),
        "HIGH": ("2", "40.00%"),
        "MODIFIER": ("1", "20.00%"),
    }


def test_a_missing_table_is_named(tmp_path, monkeypatch):
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(tmp_path))
    with pytest.raises(SystemExit, match=r"variant_annotation\.tsv not found"):
        runpy.run_path(str(SCRIPT), run_name="__main__")


def test_an_empty_table_is_refused(tmp_path, monkeypatch):
    write_table(tmp_path, [])
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(tmp_path))
    with pytest.raises(SystemExit, match="has no annotated variants"):
        runpy.run_path(str(SCRIPT), run_name="__main__")
