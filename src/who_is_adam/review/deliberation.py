from __future__ import annotations

import json
from collections.abc import Sequence

from who_is_adam.llm.base import LlmClient
from who_is_adam.models import ReviewDeliberation, SpecialistReview
from who_is_adam.review.prompts import deliberation_prompt
from who_is_adam.review.specialists import SPECIALIST_ROLES


class DeliberationError(RuntimeError):
    pass


def run_review_deliberation(
    *,
    specialist_reviews: Sequence[SpecialistReview],
    llm_client: LlmClient,
) -> ReviewDeliberation:
    _validate_specialist_set(specialist_reviews)
    reviews_json = json.dumps(
        [review.model_dump(mode="json") for review in specialist_reviews],
        ensure_ascii=False,
        sort_keys=True,
    )
    payload = llm_client.complete_json(
        deliberation_prompt(specialist_reviews_json=reviews_json),
        ReviewDeliberation,
        safety_context={
            "evidence_trust": "untrusted",
            "deliberation_mode": "devil_advocate_meta_review",
            "replaces_specialist_reviews": "false",
        },
    )
    report = ReviewDeliberation.model_validate(payload)
    _validate_deliberation(report)
    return report


def _validate_specialist_set(reviews: Sequence[SpecialistReview]) -> None:
    expected = {role.name for role in SPECIALIST_ROLES}
    actual = {review.role for review in reviews}
    if len(reviews) != len(SPECIALIST_ROLES):
        raise DeliberationError("deliberation requires exactly five specialist reviews")
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise DeliberationError(f"specialist role mismatch; missing={missing}, extra={extra}")
    if len(actual) != len(reviews):
        raise DeliberationError("duplicate specialist review roles are not allowed")


def _validate_deliberation(report: ReviewDeliberation) -> None:
    if not report.devil_advocate.critical_objections:
        raise DeliberationError("devil's advocate must include critical objections")
    if not report.debate_rounds:
        raise DeliberationError("reviewer debate must include at least one round")
    if not report.meta_review.consistency_checks:
        raise DeliberationError("meta-review must include consistency checks")
    if not report.meta_review.validity_checks:
        raise DeliberationError("meta-review must include validity checks")
    if not report.dialectical_synthesis:
        raise DeliberationError("deliberation must include dialectical synthesis")
