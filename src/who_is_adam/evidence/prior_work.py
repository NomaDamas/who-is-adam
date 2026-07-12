"""Prior-work comparison selection with public OpenReview evidence only."""

from __future__ import annotations

import re

from who_is_adam.config import ReviewConfig
from who_is_adam.evidence.openreview import OpenReviewClient
from who_is_adam.icml.constants import MAX_DIRECT_COMPARISON_CLAIMS
from who_is_adam.models import EvidenceSpan, PaperStructure, PriorWorkComparison, PriorWorkEvidence, ProviderStatus, ReferenceEntry

_COMPARISON_PATTERN = re.compile(
    r"\b(outperform(?:s|ed|ing)?|improv(?:e|es|ed|ement)|better than|state[- ]of[- ]the[- ]art|sota|comparable to|worse than|underperform(?:s|ed|ing)?|exceed(?:s|ed|ing)?|surpass(?:es|ed|ing)?)\b",
    re.IGNORECASE,
)
_CITATION_PATTERN = re.compile(r"\[\s*(\d{1,3})\s*\]|\(([^()]{2,80}?,\s*(?:19|20)\d{2})\)")


def select_direct_comparison_claims(structure: PaperStructure, *, max_claims: int = MAX_DIRECT_COMPARISON_CLAIMS) -> tuple[EvidenceSpan, ...]:
    """Return at most five direct comparison claim spans in document order."""

    claims: list[EvidenceSpan] = []
    for page_number, page in enumerate(structure.pages, start=1):
        for sentence in _sentences(page):
            if _COMPARISON_PATTERN.search(sentence) and _CITATION_PATTERN.search(sentence):
                claims.append(EvidenceSpan(page=page_number, section="Prior work comparison", text=sentence[:1000]))
                if len(claims) >= max_claims:
                    return tuple(claims)
    return tuple(claims)


def compare_prior_work_with_openreview(
    structure: PaperStructure,
    config: ReviewConfig,
    *,
    openreview_client: OpenReviewClient | None = None,
) -> tuple[PriorWorkEvidence, ...]:
    """Attach only public OpenReview metadata to selected direct comparison claims."""

    client = openreview_client or OpenReviewClient(config)
    results: list[PriorWorkEvidence] = []
    references = structure.references
    if not references:
        return tuple(results)

    for claim_span in select_direct_comparison_claims(structure):
        reference = _best_reference_for_claim(claim_span.text, references) or references[0]
        evidence = client.public_evidence_for_reference(reference)
        comparison = _comparison_from_status(evidence.status)
        results.append(
            PriorWorkEvidence(
                reference=reference,
                claim_type="direct_comparison",
                paper_claim_span=claim_span,
                openreview_evidence=evidence,
                comparison=comparison,
            )
        )
    return tuple(results)


def _comparison_from_status(status: ProviderStatus) -> PriorWorkComparison:
    if status in {ProviderStatus.VERIFIED, ProviderStatus.WEAK_MATCH}:
        return PriorWorkComparison.MAINTAINED
    return PriorWorkComparison.UNAVAILABLE


def _best_reference_for_claim(claim: str, references: list[ReferenceEntry]) -> ReferenceEntry | None:
    claim_folded = claim.casefold()
    for reference in references:
        if reference.title and reference.title.casefold() in claim_folded:
            return reference
    years = {int(match.group(0)) for match in re.finditer(r"\b(?:19|20)\d{2}\b", claim)}
    for reference in references:
        if reference.year in years:
            return reference
    return None


def _sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]
