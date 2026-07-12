"""Markdown rendering for official ICML review output."""

from __future__ import annotations

import html
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel

from who_is_adam.models import CitationCheck, CitationStatus, RuntimeMetadata, SynthesizedReview

OFFICIAL_SECTION_ORDER: tuple[str, ...] = (
    "Summary",
    "Strengths And Weaknesses",
    "Questions",
    "Limitations",
    "Soundness",
    "Presentation",
    "Contribution",
    "Rating",
    "Confidence",
    "Ethical Concerns",
    "Reproducibility Notes",
    "Evidence",
    "Consensus",
    "Conflicts",
    "Minority Opinions",
)

SCORE_SCALE_TEXT: Mapping[str, str] = {
    "Soundness": "1 poor, 2 fair, 3 good, 4 excellent",
    "Presentation": "1 poor, 2 fair, 3 good, 4 excellent",
    "Contribution": "1 poor, 2 fair, 3 good, 4 excellent",
    "Rating": "1 strong reject, 2 reject, 3 weak reject, 4 weak accept, 5 accept, 6 strong accept",
    "Confidence": "1 low, 2 somewhat low, 3 medium, 4 high, 5 very high",
}

CITATION_STATUS_ORDER: tuple[CitationStatus, ...] = (
    CitationStatus.VERIFIED,
    CitationStatus.WEAK_MATCH,
    CitationStatus.NEEDS_REVIEW,
    CitationStatus.NOT_FOUND,
    CitationStatus.METADATA_ERROR,
    CitationStatus.UNAVAILABLE,
)


class UnknownReviewSectionError(ValueError):
    """Raised when the renderer receives a section outside its fixed schema."""


def render_review_markdown(
    review: SynthesizedReview,
    *,
    metadata: RuntimeMetadata | Mapping[str, Any] | None = None,
    appendices: Mapping[str, Any] | None = None,
    citation_checks: Sequence[CitationCheck] = (),
) -> str:
    """Render a synthesized review in the exact official section order."""
    sections = [
        _section("Summary", review.summary),
        _section("Strengths And Weaknesses", _bullets([*review.strengths, *review.weaknesses])),
        _section("Questions", _bullets(review.questions) or "None."),
        _section("Limitations", _bullets(review.limitations) or "None."),
        _score_section("Soundness", review.soundness),
        _score_section("Presentation", review.presentation),
        _score_section("Contribution", review.significance),
        _score_section("Rating", review.overall_recommendation),
        _score_section("Confidence", review.confidence),
        _section("Ethical Concerns", review.ethical_concerns),
        _section("Reproducibility Notes", review.reproducibility_notes),
        _section("Evidence", _evidence(review, citation_checks)),
        _section("Consensus", _bullets(review.consensus) or "None recorded."),
        _section("Conflicts", _bullets(review.conflicts) or "None recorded."),
        _section("Minority Opinions", _bullets(review.minority_opinions) or "None recorded."),
    ]
    rendered = "\n\n".join(sections).rstrip() + "\n"
    appendix_payload: dict[str, Any] = {}
    if metadata is not None:
        appendix_payload["metadata"] = _jsonable(metadata)
    if appendices:
        appendix_payload.update({key: _jsonable(value) for key, value in appendices.items()})
    if appendix_payload:
        rendered += "\n" + _section("Appendix: Metadata", _fenced_json(appendix_payload)) + "\n"
    return rendered


def _section(title: str, body: str) -> str:
    if title not in OFFICIAL_SECTION_ORDER and title != "Appendix: Metadata":
        raise UnknownReviewSectionError(f"unknown review section: {title}")
    return f"## {title}\n\n{body.strip()}"


def _score_section(title: str, value: int) -> str:
    return _section(title, f"{value}\n\nScale: {SCORE_SCALE_TEXT[title]}")


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item.strip()}" for item in items if item.strip())


def _evidence(review: SynthesizedReview, citation_checks: Sequence[CitationCheck]) -> str:
    paper_evidence = "\n".join(
        f"- Page {span.page}{f' ({span.section})' if span.section else ''}: {span.text.strip()}"
        for span in review.evidence
    )
    citation_evidence = _citation_evidence(citation_checks)
    return f"{paper_evidence}\n\n{citation_evidence}" if citation_evidence else paper_evidence


def _citation_evidence(checks: Sequence[CitationCheck]) -> str:
    if not checks:
        return ""
    counts = {status: 0 for status in CITATION_STATUS_ORDER}
    for check in checks:
        counts[check.status] += 1
    lines = [
        "Citation verification: "
        + ", ".join(f"{status.value}={counts[status]}" for status in CITATION_STATUS_ORDER)
    ]
    for index, check in enumerate(checks, start=1):
        details: list[str] = []
        if check.duplicate_of is not None:
            details.append(f"duplicate_of={check.duplicate_of}")
        for evidence in (
            check.crossref,
            check.semantic_scholar,
            check.openalex,
            check.arxiv,
        ):
            if evidence is None or evidence.status.value == "unavailable":
                continue
            if evidence.status.value == "verified" and check.status is CitationStatus.VERIFIED:
                continue
            provider = f"{evidence.provider}={evidence.status.value}"
            mismatch = evidence.metadata.get("mismatch_fields")
            matched_title = evidence.metadata.get("matched_title")
            if isinstance(mismatch, str):
                provider += f"; mismatch={_safe_markdown(mismatch)}"
            if isinstance(matched_title, str):
                provider += f"; matched_title={_safe_markdown(matched_title)}"
            for key in (
                "matched_venue",
                "matched_volume",
                "matched_issue",
                "matched_pages",
                "matched_publisher",
                "matched_doi",
                "matched_arxiv_id",
            ):
                matched_value = evidence.metadata.get(key)
                if isinstance(matched_value, (str, int)):
                    provider += f"; {key}={_safe_markdown(str(matched_value))}"
            safe_url = _safe_url(evidence.url)
            if safe_url:
                provider += f"; url={safe_url}"
            details.append(provider)
        if details:
            label = _safe_markdown(check.reference.title or check.reference.raw[:80])
            lines.append(
                f"- Citation [{index}] {label}: {check.status.value} | " + " | ".join(details)
            )
    return "\n".join(lines)


def _safe_markdown(value: str) -> str:
    escaped = html.escape(" ".join(value.split()), quote=True)
    escaped = re.sub(r"(?i)javascript\s*:", "javascript&#58;", escaped)
    return re.sub(r"([\\`\[\]()])", r"\\\1", escaped)


def _safe_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return _safe_markdown(value)


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def _fenced_json(value: Mapping[str, Any]) -> str:
    return "```json\n" + json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n```"
