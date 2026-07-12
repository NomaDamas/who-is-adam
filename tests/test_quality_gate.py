from __future__ import annotations

from pathlib import Path

from who_is_adam.models import GateStatus
from who_is_adam.pdf.extractor import PdfExtractor
from who_is_adam.safety.quality_gate import evaluate_quality, evaluate_pre_review_gates


def test_valid_fixture_extraction_metrics_are_deterministic(pdf_fixtures: Path) -> None:
    paper = PdfExtractor().extract(pdf_fixtures / "valid_icml_text.pdf")

    metrics = paper.extraction_metrics
    assert paper.title == "Deterministic ICML Fixture for Safety Gates"
    assert metrics.page_count == 2
    assert metrics.extracted_text_chars > 2_000
    assert metrics.low_text_pages == []
    assert metrics.ocr_used is False
    assert metrics.encrypted is False
    assert len(paper.sections) >= 2
    assert paper.tables
    assert paper.figures
    assert paper.formulas
    assert len(paper.references) == 2

    result = evaluate_quality(paper)
    assert result.status is GateStatus.PASS
    assert result.reasons == []


def test_low_text_scan_like_fixture_rejects_without_ocr_dependency(pdf_fixtures: Path) -> None:
    paper = PdfExtractor().extract(pdf_fixtures / "low_text_scan_like.pdf")

    metrics = paper.extraction_metrics
    assert metrics.page_count == 3
    assert metrics.extracted_text_chars < 200
    assert metrics.low_text_pages == [1, 2, 3]
    assert metrics.ocr_used is False

    result = evaluate_quality(paper)
    assert result.status is GateStatus.REJECT
    assert any("extracted text too short" in reason for reason in result.reasons)
    assert any("too many low-text pages" in reason for reason in result.reasons)
    assert any("abstract was not detected" in reason for reason in result.reasons)
    assert any("references were not detected" in reason for reason in result.reasons)
    assert {span.page for span in result.evidence} == {1, 2, 3}


def test_pre_review_gate_is_fail_closed_for_low_quality_before_safety(pdf_fixtures: Path) -> None:
    paper = PdfExtractor().extract(pdf_fixtures / "low_text_scan_like.pdf")

    result = evaluate_pre_review_gates(paper)

    assert result.status is GateStatus.REJECT
    assert all("prompt injection" not in reason for reason in result.reasons)
