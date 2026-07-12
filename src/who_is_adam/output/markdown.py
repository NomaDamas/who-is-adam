"""Markdown rendering for official ICML review output."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from who_is_adam.models import RuntimeMetadata, SynthesizedReview

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


def render_review_markdown(
    review: SynthesizedReview,
    *,
    metadata: RuntimeMetadata | Mapping[str, Any] | None = None,
    appendices: Mapping[str, Any] | None = None,
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
        _section("Evidence", _evidence(review)),
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
        raise ValueError(f"unknown review section: {title}")
    return f"## {title}\n\n{body.strip()}"


def _score_section(title: str, value: int) -> str:
    return _section(title, f"{value}\n\nScale: {SCORE_SCALE_TEXT[title]}")


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item.strip()}" for item in items if item.strip())


def _evidence(review: SynthesizedReview) -> str:
    return "\n".join(
        f"- Page {span.page}"
        f"{f' ({span.section})' if span.section else ''}: {span.text.strip()}"
        for span in review.evidence
    )


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def _fenced_json(value: Mapping[str, Any]) -> str:
    return "```json\n" + json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n```"
