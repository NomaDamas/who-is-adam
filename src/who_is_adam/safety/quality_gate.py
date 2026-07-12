"""Fail-closed extraction quality gate for review inputs."""

from __future__ import annotations

from dataclasses import dataclass

from who_is_adam.models import EvidenceSpan, GateResult, GateStatus, PaperStructure
from who_is_adam.safety.prompt_injection import detect_prompt_injection


@dataclass(frozen=True)
class QualityThresholds:
    """Deterministic thresholds for deciding whether PDF text is reviewable."""

    min_total_chars: int = 2000
    min_chars_per_page: int = 200
    max_low_text_page_ratio: float = 0.35
    min_sections: int = 2
    require_abstract: bool = True
    require_references: bool = True


DEFAULT_THRESHOLDS = QualityThresholds()


def evaluate_quality(structure: PaperStructure, thresholds: QualityThresholds = DEFAULT_THRESHOLDS) -> GateResult:
    """Return reject diagnostics when extraction is too weak for review."""

    reasons: list[str] = []
    evidence: list[EvidenceSpan] = []
    metrics = structure.extraction_metrics

    if metrics.encrypted:
        reasons.append("encrypted PDF cannot be reviewed")
    if metrics.extracted_text_chars < thresholds.min_total_chars:
        reasons.append(
            f"extracted text too short: {metrics.extracted_text_chars} < {thresholds.min_total_chars} characters"
        )
    low_ratio = len(metrics.low_text_pages) / metrics.page_count
    if low_ratio > thresholds.max_low_text_page_ratio:
        reasons.append(
            f"too many low-text pages: {len(metrics.low_text_pages)}/{metrics.page_count} pages below {thresholds.min_chars_per_page} characters"
        )
        for page in metrics.low_text_pages[:5]:
            page_text = structure.pages[page - 1] if page - 1 < len(structure.pages) else ""
            evidence.append(EvidenceSpan(page=page, section="Extraction quality", text=page_text[:200] or "Low text page"))
    if len(structure.sections) < thresholds.min_sections:
        reasons.append(f"insufficient section detection: {len(structure.sections)} < {thresholds.min_sections}")
    if thresholds.require_abstract and _missing_abstract(structure.abstract):
        reasons.append("abstract was not detected")
    if thresholds.require_references and not structure.references:
        reasons.append("references were not detected")

    if reasons:
        if not evidence:
            evidence.append(EvidenceSpan(page=1, section="Extraction quality", text=(structure.pages[0] if structure.pages else "No extracted text")[:500] or "No extracted text"))
        return GateResult(status=GateStatus.REJECT, reasons=reasons, evidence=evidence)
    return GateResult(status=GateStatus.PASS)


def evaluate_pre_review_gates(
    structure: PaperStructure,
    thresholds: QualityThresholds = DEFAULT_THRESHOLDS,
) -> GateResult:
    """Apply quality first, then prompt-injection safety before any review generation."""

    quality = evaluate_quality(structure, thresholds)
    if quality.status is GateStatus.REJECT:
        return quality
    injection = detect_prompt_injection(structure)
    if injection.status is GateStatus.REJECT:
        return injection
    return GateResult(status=GateStatus.PASS)


def _missing_abstract(abstract: str) -> bool:
    normalized = abstract.strip().lower()
    return not normalized or normalized == "no abstract detected." or len(normalized) < 50
