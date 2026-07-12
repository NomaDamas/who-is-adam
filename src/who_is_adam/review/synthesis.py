"""Synthesis of independent specialist reviews."""

from __future__ import annotations

import json
from collections.abc import Sequence

from who_is_adam.llm.base import LlmClient
from who_is_adam.models import SpecialistReview, SynthesizedReview
from who_is_adam.review.prompts import synthesis_prompt
from who_is_adam.review.specialists import SPECIALIST_ROLES


class SynthesisError(RuntimeError):
    """Raised when synthesis omits required independent-review information."""


def synthesize_reviews(
    *,
    specialist_reviews: Sequence[SpecialistReview],
    llm_client: LlmClient,
) -> SynthesizedReview:
    """Validate and synthesize five independent specialist reviews."""
    _validate_specialist_set(specialist_reviews)
    reviews_json = json.dumps(
        [review.model_dump(mode="json") for review in specialist_reviews],
        ensure_ascii=False,
        sort_keys=True,
    )
    payload = llm_client.complete_json(
        synthesis_prompt(specialist_reviews_json=reviews_json),
        SynthesizedReview,
        safety_context={
            "evidence_trust": "untrusted",
            "peer_outputs_visible_before_synthesis": "false",
        },
    )
    review = SynthesizedReview.model_validate(payload)
    _validate_synthesis(review)
    return review


def _validate_specialist_set(reviews: Sequence[SpecialistReview]) -> None:
    expected = {role.name for role in SPECIALIST_ROLES}
    actual = {review.role for review in reviews}
    if len(reviews) != len(SPECIALIST_ROLES):
        raise SynthesisError("synthesis requires exactly five specialist reviews")
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise SynthesisError(f"specialist role mismatch; missing={missing}, extra={extra}")
    if len(actual) != len(reviews):
        raise SynthesisError("duplicate specialist review roles are not allowed")


def _validate_synthesis(review: SynthesizedReview) -> None:
    if not review.consensus:
        raise SynthesisError("synthesis must preserve consensus statements")
    if review.conflicts is None or review.minority_opinions is None:
        raise SynthesisError("synthesis must explicitly preserve conflicts and minority opinions")
    if not review.evidence:
        raise SynthesisError("synthesis must include supporting evidence")
