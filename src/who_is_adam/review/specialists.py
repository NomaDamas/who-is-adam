"""Independent specialist review orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from who_is_adam.llm.base import LlmClient
from who_is_adam.models import CitationCheck, PaperStructure, SpecialistReview
from who_is_adam.review.prompts import specialist_prompt


@dataclass(frozen=True, slots=True)
class SpecialistRole:
    """A single independent review perspective."""

    name: str
    remit: str


SPECIALIST_ROLES: tuple[SpecialistRole, ...] = (
    SpecialistRole(
        name="methodology",
        remit="Assess technical soundness, assumptions, proofs, algorithms, and experimental design.",
    ),
    SpecialistRole(
        name="empirical-evidence",
        remit="Assess datasets, baselines, metrics, ablations, statistical support, and reproducibility evidence.",
    ),
    SpecialistRole(
        name="novelty-significance",
        remit="Assess originality, relation to prior work, contribution clarity, and likely ICML impact.",
    ),
    SpecialistRole(
        name="presentation-clarity",
        remit="Assess organization, writing clarity, figures, tables, notation, and reader burden.",
    ),
    SpecialistRole(
        name="ethics-reproducibility",
        remit="Assess ethics, limitations, societal risks, artifact availability, and reproducibility claims.",
    ),
)


class SpecialistReviewError(RuntimeError):
    """Raised when an independent specialist review is missing or invalid."""


def run_specialist_reviews(
    *,
    paper: PaperStructure,
    llm_client: LlmClient,
    citation_checks: tuple[CitationCheck, ...] = (),
    roles: tuple[SpecialistRole, ...] = SPECIALIST_ROLES,
) -> tuple[SpecialistReview, ...]:
    """Run five independent specialist reviews without sharing peer outputs."""
    if len(roles) != 5:
        raise SpecialistReviewError("exactly five specialist roles are required")
    if len({role.name for role in roles}) != len(roles):
        raise SpecialistReviewError("specialist role names must be unique")

    reviews: list[SpecialistReview] = []
    for role in roles:
        prompt = specialist_prompt(
            role=role.name,
            remit=role.remit,
            paper=paper,
            citation_checks=citation_checks,
        )
        payload = llm_client.complete_json(
            prompt,
            SpecialistReview,
            safety_context={
                "evidence_trust": "untrusted",
                "role": role.name,
                "peer_outputs_visible": "false",
            },
        )
        review = SpecialistReview.model_validate(payload)
        if review.role != role.name:
            raise SpecialistReviewError(
                f"specialist {role.name!r} returned mismatched role {review.role!r}"
            )
        reviews.append(review)
    return tuple(reviews)
