"""Paper-level citation verification orchestration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

from who_is_adam.config import ReviewConfig
from who_is_adam.models import (
    CitationCheck,
    CitationStatus,
    PaperStructure,
    ProviderEvidence,
    ProviderStatus,
)

from .arxiv import verify_arxiv_citation
from .citation_metadata import normalized_reference_key
from .citations import ProviderRequestBudget, combine_citation_status, unavailable_provider
from .crossref import verify_crossref_citation
from .openalex import verify_openalex_citation
from .semantic_scholar import verify_semantic_scholar_citation

MAX_CITATIONS_TO_VERIFY: Final = 100
MAX_PROVIDER_REQUESTS: Final = 60


def verify_paper_citations(paper: PaperStructure, config: ReviewConfig) -> list[CitationCheck]:
    """Verify every parsed reference and retain duplicate/provider-conflict evidence."""
    checks: list[CitationCheck] = []
    seen: dict[str, int] = {}
    verified_count = 0
    circuits: dict[str, str] = {}
    request_budget = ProviderRequestBudget(remaining=MAX_PROVIDER_REQUESTS)
    for index, reference in enumerate(paper.references, start=1):
        duplicate_key = normalized_reference_key(reference)
        duplicate_of = seen.get(duplicate_key) if duplicate_key is not None else None
        if duplicate_key is not None and duplicate_of is None:
            seen[duplicate_key] = index

        if duplicate_of is not None:
            original = checks[duplicate_of - 1]
            checks.append(
                original.model_copy(update={"reference": reference, "duplicate_of": duplicate_of})
            )
            continue

        if verified_count >= MAX_CITATIONS_TO_VERIFY:
            diagnostic = f"citation verification limit exceeded ({MAX_CITATIONS_TO_VERIFY})"
            checks.append(
                CitationCheck(
                    reference=reference,
                    crossref=unavailable_provider("crossref", diagnostic),
                    semantic_scholar=unavailable_provider("semantic_scholar", diagnostic),
                    openalex=unavailable_provider("openalex", diagnostic),
                    arxiv=(
                        unavailable_provider("arxiv", diagnostic) if reference.arxiv_id else None
                    ),
                    status=CitationStatus.UNAVAILABLE,
                )
            )
            continue
        verified_count += 1

        crossref = _provider_result(
            "crossref",
            circuits,
            lambda: verify_crossref_citation(reference, config, request_budget=request_budget),
        )
        semantic_scholar = _provider_result(
            "semantic_scholar",
            circuits,
            lambda: verify_semantic_scholar_citation(
                reference, config, request_budget=request_budget
            ),
        )
        openalex = _provider_result(
            "openalex",
            circuits,
            lambda: verify_openalex_citation(reference, config, request_budget=request_budget),
        )
        arxiv = (
            _provider_result(
                "arxiv",
                circuits,
                lambda: verify_arxiv_citation(reference, config, request_budget=request_budget),
            )
            if reference.arxiv_id
            else None
        )
        provisional = CitationCheck(
            reference=reference,
            crossref=crossref,
            semantic_scholar=semantic_scholar,
            openalex=openalex,
            arxiv=arxiv,
            status=CitationStatus.UNAVAILABLE,
        )
        checks.append(
            provisional.model_copy(update={"status": combine_citation_status(provisional)})
        )
    return checks


def _provider_result(
    provider: str,
    circuits: dict[str, str],
    verify: Callable[[], ProviderEvidence],
) -> ProviderEvidence:
    if provider in circuits:
        return unavailable_provider(provider, f"provider circuit open after {circuits[provider]}")
    evidence = verify()
    if _opens_circuit(evidence):
        circuits[provider] = evidence.diagnostic or "provider unavailable"
    return evidence


def _opens_circuit(evidence: ProviderEvidence) -> bool:
    diagnostic = evidence.diagnostic or ""
    return evidence.status is ProviderStatus.UNAVAILABLE and (
        diagnostic == "HTTP 429" or diagnostic.startswith("HTTP 5")
    )
