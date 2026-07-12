"""Semantic Scholar citation fact verification client."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

import httpx

from who_is_adam.config import ReviewConfig
from who_is_adam.models import ProviderEvidence, ProviderStatus, ReferenceEntry

from .citations import (
    ProviderHttpClient,
    ProviderRequestBudget,
    ProviderResult,
    classify_reference_match,
    identifier_fallback_evidence,
    make_provider_http_client,
    select_best_candidate,
)

FIELDS = "title,year,url,externalIds,authors,venue,publicationVenue"


class SemanticScholarClient:
    def __init__(
        self,
        config: ReviewConfig,
        *,
        client: httpx.Client | None = None,
        request_budget: ProviderRequestBudget | None = None,
    ) -> None:
        self.http = make_provider_http_client(
            "semantic_scholar",
            config.semantic_scholar,
            offline=config.offline,
            client=client,
            request_budget=request_budget,
        )

    def close(self) -> None:
        self.http.close()

    def verify(self, reference: ReferenceEntry) -> ProviderEvidence:
        failed_identifiers: list[tuple[str, str]] = []
        if reference.doi:
            exact = self._lookup_by_id(reference, f"DOI:{reference.doi}")
            if exact.diagnostic != "HTTP 404":
                return _require_failed_identifiers(exact, failed_identifiers)
            failed_identifiers.append(("DOI", "doi_match"))
        if reference.arxiv_id:
            exact = self._lookup_by_id(reference, f"ARXIV:{reference.arxiv_id}")
            if exact.diagnostic != "HTTP 404":
                return _require_failed_identifiers(exact, failed_identifiers)
            failed_identifiers.append(("arXiv ID", "arxiv_id_match"))
        if not reference.title:
            return ProviderResult(
                "semantic_scholar",
                ProviderStatus.UNAVAILABLE,
                "reference has no DOI, arXiv id, or title",
            ).evidence()
        return _require_failed_identifiers(self._search_by_title(reference), failed_identifiers)

    def _search_by_title(self, reference: ReferenceEntry) -> ProviderEvidence:
        assert reference.title is not None
        data, error = self.http.get_json(
            "paper/search",
            params={"query": reference.title, "limit": 5, "fields": FIELDS},
        )
        if error:
            return error.evidence()
        papers = (data or {}).get("data")
        if not isinstance(papers, list) or not papers:
            return ProviderResult(
                "semantic_scholar", ProviderStatus.NOT_FOUND, "no Semantic Scholar paper found"
            ).evidence()
        candidates = [paper for paper in papers if isinstance(paper, dict)]
        candidate = select_best_candidate(reference, candidates)
        if candidate is None:
            return ProviderResult(
                "semantic_scholar",
                ProviderStatus.NOT_FOUND,
                "no Semantic Scholar candidate met the title threshold",
            ).evidence()
        return self._classified(reference, candidate)

    def _lookup_by_id(self, reference: ReferenceEntry, paper_id: str) -> ProviderEvidence:
        data, error = self.http.get_json(
            f"paper/{quote(paper_id, safe='')}", params={"fields": FIELDS}
        )
        if error:
            return error.evidence()
        if not isinstance(data, dict):
            return ProviderResult(
                "semantic_scholar",
                ProviderStatus.METADATA_ERROR,
                "Semantic Scholar response missing paper object",
            ).evidence()
        return self._classified(reference, dict(data))

    @staticmethod
    def _classified(reference: ReferenceEntry, candidate: Mapping[str, Any]) -> ProviderEvidence:
        result = classify_reference_match(reference, candidate)
        raw_url = candidate.get("url")
        url = raw_url if isinstance(raw_url, str) else None
        return ProviderResult(
            "semantic_scholar", result.status, result.diagnostic, url, result.metadata
        ).evidence()


def verify_semantic_scholar_citation(
    reference: ReferenceEntry,
    config: ReviewConfig,
    *,
    client: httpx.Client | None = None,
    request_budget: ProviderRequestBudget | None = None,
) -> ProviderEvidence:
    provider = SemanticScholarClient(config, client=client, request_budget=request_budget)
    try:
        return provider.verify(reference)
    finally:
        provider.close()


def _require_failed_identifiers(
    evidence: ProviderEvidence,
    failed_identifiers: list[tuple[str, str]],
) -> ProviderEvidence:
    for identifier, metadata_key in failed_identifiers:
        evidence = identifier_fallback_evidence(evidence, identifier, metadata_key)
    return evidence


__all__ = ["ProviderHttpClient", "SemanticScholarClient", "verify_semantic_scholar_citation"]
