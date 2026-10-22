"""Runs scripts/reference.py on tiny single-sample VCFs.

Skipped where tiledbvcf is not installed or bcftools (used here to bgzip and index the inputs) is
not on PATH.
"""

import csv
import runpy
import shutil
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("tiledbvcf")
pytestmark = pytest.mark.skipif(shutil.which("bcftools") is None, reason="bcftools not on PATH")

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reference.py"

# The script queries 17:7668402-7687550 and 13:32315474-32400266 (GRCh38) by default.
# Positions are synthetic; only their place inside or outside those regions matters.
RECORDS = {
    "S1": [
        ("13", 32316000, "A", "G", "0/1"),
        ("17", 1000, "C", "T", "0/1"),  # outside both regions
        ("17", 7670000, "G", "A", "1/1"),
    ],
    "S2": [("17", 7675000, "T", "C", "0/1")],
    "S3": [("13", 32320000, "C", "A", "0/1")],
}


def write_vcf(work: Path, sample: str, contig_prefix: str = "") -> None:
    lines = [
        "##fileformat=VCFv4.2",
        f"##contig=<ID={contig_prefix}13,length=114364328>",
        f"##contig=<ID={contig_prefix}17,length=83257441>",
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
        "\t".join(
            ["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO", "FORMAT", sample]
        ),
    ]
    lines += [
        f"{contig_prefix}{c}\t{pos}\t.\t{ref}\t{alt}\t50\tPASS\t.\tGT\t{gt}"
        for c, pos, ref, alt, gt in RECORDS[sample]
    ]
    plain = work / f"{sample}.vcf"
    plain.write_text("\n".join(lines) + "\n", encoding="utf-8")
    gz = work / f"{sample}.vcf.gz"
    subprocess.run(["bcftools", "view", "-Oz", "-o", str(gz), str(plain)], check=True)
    subprocess.run(["bcftools", "index", "-t", str(gz)], check=True)
    plain.unlink()


def run(tmp_path: Path, monkeypatch) -> list[dict]:
    monkeypatch.setenv("AISCIENTIST_WORK", str(tmp_path / "work"))
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(tmp_path / "results"))
    runpy.run_path(str(SCRIPT), run_name="__main__")
    with (tmp_path / "results" / "tables" / "cohort_region_variants.tsv").open() as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def test_ingests_samples_and_queries_the_regions(tmp_path, monkeypatch, capsys):
    work = tmp_path / "work"
    work.mkdir()
    write_vcf(work, "S1")
    write_vcf(work, "S2")
    rows = run(tmp_path, monkeypatch)
    assert sorted((r["sample_name"], r["contig"], r["pos_start"]) for r in rows) == [
        ("S1", "13", "32316000"),
        ("S1", "17", "7670000"),
        ("S2", "17", "7675000"),
    ]
    assert (work / "variant_db").is_dir()
    assert "2 sample(s); 3 variant-records" in capsys.readouterr().out


def test_a_rerun_ingests_only_new_samples(tmp_path, monkeypatch, capsys):
    work = tmp_path / "work"
    work.mkdir()
    write_vcf(work, "S1")
    write_vcf(work, "S2")
    run(tmp_path, monkeypatch)
    write_vcf(work, "S3")
    capsys.readouterr()
    rows = run(tmp_path, monkeypatch)
    out = capsys.readouterr().out
    assert "2 VCF(s) already ingested; skipped" in out
    assert "3 sample(s); 4 variant-records" in out  # not 7: S1 and S2 are not added twice
    assert sorted(r["sample_name"] for r in rows) == ["S1", "S1", "S2", "S3"]


def test_regions_must_use_the_vcf_contig_names(tmp_path, monkeypatch, capsys):
    work = tmp_path / "work"
    work.mkdir()
    write_vcf(work, "S1", contig_prefix="chr")  # chr17, but the default regions say 17
    rows = run(tmp_path, monkeypatch)
    assert rows == []
    assert "1 sample(s); 0 variant-records" in capsys.readouterr().out
