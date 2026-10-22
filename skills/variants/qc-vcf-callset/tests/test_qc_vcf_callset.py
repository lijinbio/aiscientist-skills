"""Runs scripts/reference.py on a tiny two-sample VCF through each of its three methods.

The bcftools test is skipped where bcftools is not on PATH and the cyvcf2 test where cyvcf2 is not
installed. The plain-Python fallback needs neither, so it runs everywhere.
"""

import csv
import json
import runpy
import shutil
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reference.py"

HEADER = (
    "##fileformat=VCFv4.2\n"
    "##contig=<ID=1,length=1000>\n"
    '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n'
    "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\tS2\n"
)
# Two transitions (A>G, C>T), two transversions (A>C, G>T) and one deletion, so Ti/Tv = 1.0.
# S1: 3 het SNPs, 1 hom-alt SNP, 1 het deletion. S2: 1 het SNP, 2 hom-ref SNPs, 2 missing calls.
# 10 genotypes, 2 missing: call rate 0.8.
RECORDS = [
    ("100", "A", "G", "0/1", "0/0"),
    ("200", "C", "T", "1/1", "0/1"),
    ("300", "A", "C", "0/1", "./."),
    ("400", "G", "T", "0/1", "0/0"),
    ("500", "AT", "A", "0/1", "./."),
]


def write_vcf(path: Path, records=RECORDS) -> None:
    body = "".join(
        f"1\t{pos}\t.\t{ref}\t{alt}\t50\tPASS\t.\tGT\t{s1}\t{s2}\n"
        for pos, ref, alt, s1, s2 in records
    )
    path.write_text(HEADER + body, encoding="utf-8")


def run(tmp_path: Path, monkeypatch, seq_type: str = "WGS", records=RECORDS) -> dict:
    vcf = tmp_path / "calls.vcf"
    write_vcf(vcf, records)
    monkeypatch.setenv("AISCIENTIST_DATASET", str(vcf))
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(tmp_path / "results"))
    monkeypatch.setenv("AISCIENTIST_SEQ_TYPE", seq_type)
    runpy.run_path(str(SCRIPT), run_name="__main__")
    return json.loads((tmp_path / "results" / "data" / "vcf_qc.json").read_text())


def hide_bcftools(monkeypatch) -> None:
    real_which = shutil.which
    monkeypatch.setattr(
        shutil,
        "which",
        lambda cmd, *a, **k: None if cmd == "bcftools" else real_which(cmd, *a, **k),
    )


def hide_cyvcf2(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "cyvcf2", None)  # makes `from cyvcf2 import VCF` fail


@pytest.mark.skipif(shutil.which("bcftools") is None, reason="bcftools not on PATH")
def test_bcftools_stats_gives_all_metrics_and_flags(tmp_path, monkeypatch):
    m = run(tmp_path, monkeypatch)
    assert m["method"] == "bcftools stats"
    assert (m["n_records"], m["n_snps"], m["n_indels"], m["n_multiallelic"]) == (5, 4, 1, 0)
    assert m["n_samples"] == 2
    assert m["ti_tv"] == 1.0
    assert m["het_hom"] == 4.0  # SNPs only: 4 het / 1 hom-alt
    assert m["call_rate"] == 0.8  # 8 of 10 genotypes called; hom-ref calls count as called
    flags = " ".join(m["qc_flags"])
    assert "Ti/Tv 1.0 outside WGS" in flags
    assert "Het/Hom 4.0" in flags
    assert "Call rate 80.0%" in flags
    with (tmp_path / "results" / "tables" / "vcf_qc_summary.csv").open() as fh:
        table = {row["metric"]: row["value"] for row in csv.DictReader(fh)}
    assert table["ti_tv"] == "1.0"
    assert table["n_records"] == "5"


def test_cyvcf2_fallback_counts_genotypes(tmp_path, monkeypatch):
    pytest.importorskip("cyvcf2")
    hide_bcftools(monkeypatch)
    m = run(tmp_path, monkeypatch)
    assert m["method"] == "cyvcf2"
    assert (m["n_snps"], m["n_indels"], m["n_samples"]) == (4, 1, 2)
    assert m["ti_tv"] == 1.0
    assert m["het_hom"] == 5.0  # all records, the deletion included: 5 het / 1 hom-alt
    assert m["call_rate"] == 0.8
    assert any(f.startswith("Call rate") for f in m["qc_flags"])


def test_plain_python_fallback_gives_ti_tv_only(tmp_path, monkeypatch):
    hide_bcftools(monkeypatch)
    hide_cyvcf2(monkeypatch)
    m = run(tmp_path, monkeypatch)
    assert m["method"].startswith("stdlib scan")
    assert (m["n_snps"], m["n_indels"], m["ti_tv"]) == (4, 1, 1.0)
    assert m["het_hom"] is None and m["call_rate"] is None
    assert len(m["qc_flags"]) == 1 and m["qc_flags"][0].startswith("Ti/Tv 1.0")


def test_seq_type_sets_the_ti_tv_band(tmp_path, monkeypatch):
    hide_bcftools(monkeypatch)
    hide_cyvcf2(monkeypatch)
    records = [  # two transitions, one transversion: Ti/Tv = 2.0
        ("100", "A", "G", "0/1", "0/1"),
        ("200", "C", "T", "0/1", "0/1"),
        ("300", "A", "C", "0/1", "0/1"),
    ]
    (tmp_path / "wgs").mkdir()
    (tmp_path / "wes").mkdir()
    wgs = run(tmp_path / "wgs", monkeypatch, "WGS", records)
    wes = run(tmp_path / "wes", monkeypatch, "WES", records)
    assert wgs["ti_tv"] == wes["ti_tv"] == 2.0
    assert wgs["qc_flags"] == []  # within the WGS band 1.8-2.5
    assert wes["qc_flags"][0].startswith("Ti/Tv 2.0 outside WES")  # below the WES band 2.5-3.5


def test_a_missing_vcf_is_named(tmp_path, monkeypatch):
    monkeypatch.setenv("AISCIENTIST_DATASET", str(tmp_path / "absent.vcf.gz"))
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(tmp_path / "results"))
    with pytest.raises(SystemExit, match="input VCF not found"):
        runpy.run_path(str(SCRIPT), run_name="__main__")
