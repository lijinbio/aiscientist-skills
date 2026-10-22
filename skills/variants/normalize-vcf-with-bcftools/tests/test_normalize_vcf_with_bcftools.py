"""Runs scripts/reference.py on a tiny VCF and a 60-base reference.

Needs bcftools on PATH; those tests are skipped where it is missing. The missing-bcftools test runs
everywhere.
"""

import gzip
import json
import runpy
import shutil
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reference.py"
needs_bcftools = pytest.mark.skipif(shutil.which("bcftools") is None, reason="bcftools not on PATH")

# Positions 12-19 are a CA repeat (CACACACA), so deleting one CA unit has many representations.
REF = "ACGTACGTACTCACACACAGGATTACAGATTACCGGTTAACCGGTTAACCGGTTAACCGG"

VCF = (
    "##fileformat=VCFv4.2\n"
    "##contig=<ID=chr1,length=60>\n"
    '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n'
    "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\n"
    "chr1\t3\t.\tG\tA,T\t50\tPASS\t.\tGT\t1/2\n"  # multiallelic SNP: split into two records
    "chr1\t17\t.\tACA\tA\t50\tPASS\t.\tGT\t0/1\n"  # CA deletion at the right end of the repeat
    "chr1\t22\t.\tAT\tGC\t50\tPASS\t.\tGT\t0/1\n"  # MNP: atomized into two SNPs
    "chr1\t35\t.\tG\tA\t50\tPASS\t.\tGT\t0/1\n"  # plain SNP: unchanged
)


def stage(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    work, art = tmp_path / "work", tmp_path / "results"
    work.mkdir()
    fasta = tmp_path / "ref.fa"
    fasta.write_text(f">chr1\n{REF}\n", encoding="utf-8")
    # name, length, byte offset of the sequence, bases per line, bytes per line
    (tmp_path / "ref.fa.fai").write_text(f"chr1\t{len(REF)}\t6\t{len(REF)}\t{len(REF) + 1}\n")
    vcf = work / "input.vcf"
    vcf.write_text(VCF, encoding="utf-8")
    monkeypatch.setenv("AISCIENTIST_WORK", str(work))
    monkeypatch.setenv("AISCIENTIST_ARTIFACTS", str(art))
    monkeypatch.setenv("AISCIENTIST_DATASET", str(vcf))
    monkeypatch.setenv("AISCIENTIST_REF_FASTA", str(fasta))
    return work, art


def records(vcf_gz: Path) -> list[tuple[int, str, str, str]]:
    with gzip.open(vcf_gz, "rt") as fh:
        rows = [line.rstrip("\n").split("\t") for line in fh if not line.startswith("#")]
    return [(int(r[1]), r[3], r[4], r[9]) for r in rows]


@needs_bcftools
def test_splits_atomizes_and_left_aligns(tmp_path, monkeypatch, capsys):
    work, art = stage(tmp_path, monkeypatch)
    runpy.run_path(str(SCRIPT), run_name="__main__")

    out = work / "normalized.vcf.gz"
    assert records(out) == [
        (3, "G", "A", "1/0"),  # no spurious G>* records, genotypes kept per allele
        (3, "G", "T", "0/1"),
        (11, "TCA", "T", "0/1"),  # the deletion moved to the left end of the repeat
        (22, "A", "G", "0/1"),
        (23, "T", "C", "0/1"),
        (35, "G", "A", "0/1"),
    ]
    assert (work / "normalized.vcf.gz.tbi").exists()
    summary = json.loads((art / "data" / "normalization_summary.json").read_text())
    assert (summary["records_before"], summary["records_after"]) == (4, 6)
    assert summary["normalized_vcf"] == str(out)
    assert json.loads(capsys.readouterr().out) == summary


@needs_bcftools
def test_a_missing_reference_is_refused(tmp_path, monkeypatch):
    stage(tmp_path, monkeypatch)
    monkeypatch.setenv("AISCIENTIST_REF_FASTA", str(tmp_path / "absent.fa"))
    with pytest.raises(SystemExit, match="AISCIENTIST_REF_FASTA"):
        runpy.run_path(str(SCRIPT), run_name="__main__")


@needs_bcftools
def test_a_reference_that_does_not_match_fails_loudly(tmp_path, monkeypatch):
    stage(tmp_path, monkeypatch)
    (tmp_path / "ref.fa").write_text(f">chr1\n{'T' * len(REF)}\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="bcftools norm failed"):
        runpy.run_path(str(SCRIPT), run_name="__main__")


@needs_bcftools
def test_a_missing_vcf_is_named(tmp_path, monkeypatch):
    stage(tmp_path, monkeypatch)
    monkeypatch.setenv("AISCIENTIST_DATASET", str(tmp_path / "absent.vcf.gz"))
    with pytest.raises(SystemExit, match="input VCF not found"):
        runpy.run_path(str(SCRIPT), run_name="__main__")


def test_without_bcftools_it_stops_with_a_clear_message(tmp_path, monkeypatch):
    stage(tmp_path, monkeypatch)
    monkeypatch.setattr(shutil, "which", lambda *a, **k: None)
    with pytest.raises(SystemExit, match="bcftools not found"):
        runpy.run_path(str(SCRIPT), run_name="__main__")
