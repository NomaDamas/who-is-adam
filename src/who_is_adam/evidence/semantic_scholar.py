"""Semantic Scholar citation fact verification client."""

from __future__ import annotations

from urllib.parse import quote

import httpx

from who_is_adam.config import ReviewConfig
from who_is_adam.models import ProviderEvidence, ProviderStatus, ReferenceEntry

from .citations import ProviderHttpClient, ProviderResult, classify_reference_match, make_provider_http_client


class SemanticScholarClient:
    def __init__(self, config: ReviewConfig, *, client: httpx.Client | None = None) -> None:
        self.http = make_provider_http_client(
            "semantic_scholar", config.semantic_scholar, offline=config.offline, client=client
        )

    def verify(self, reference: ReferenceEntry) -> ProviderEvidence:
        if reference.doi:
            return self._lookup_by_id(reference, f"DOI:{reference.doi}")
        if reference.arxiv_id:
            return self._lookup_by_id(reference, f"ARXIV:{reference.arxiv_id}")
        if not reference.title:
            return ProviderResult("semantic_scholar", ProviderStatus.UNAVAILABLE, "reference has no DOI, arXiv id, or title").evidence()
        data, error = self.http.get_json(
            "paper/search",
            params={"query": reference.title, "limit": 1, "fields": "title,year,url,externalIds"},
        )
        if error:
            return error.evidence()
        papers = (data or {}).get("data")
        if not isinstance(papers, list) or not papers:
            return ProviderResult("semantic_scholar", ProviderStatus.NOT_FOUND, "no Semantic Scholar paper found").evidence()
        candidate = papers[0]
        if not isinstance(candidate, dict):
            return ProviderResult("semantic_scholar", ProviderStatus.METADATA_ERROR, "Semantic Scholar paper was not an object").evidence()
        return self._classified(reference, candidate)

    def _lookup_by_id(self, reference: ReferenceEntry, paper_id: str) -> ProviderEvidence:
        data, error = self.http.get_json(
            f"paper/{quote(paper_id, safe='')}", params={"fields": "title,year,url,externalIds"}
        )
        if error:
            return error.evidence()
        if not isinstance(data, dict):
            return ProviderResult("semantic_scholar", ProviderStatus.METADATA_ERROR, "Semantic Scholar response missing paper object").evidence()
        return self._classified(reference, dict(data))

    @staticmethod
    def _classified(reference: ReferenceEntry, candidate: dict[str, object]) -> ProviderEvidence:
        result = classify_reference_match(reference, candidate)
        raw_url = candidate.get("url")
        url = raw_url if isinstance(raw_url, str) else None
        return ProviderResult("semantic_scholar", result.status, result.diagnostic, url, result.metadata).evidence()


def verify_semantic_scholar_citation(
    reference: ReferenceEntry, config: ReviewConfig, *, client: httpx.Client | None = None
) -> ProviderEvidence:
    return SemanticScholarClient(config, client=client).verify(reference)


__all__ = ["ProviderHttpClient", "SemanticScholarClient", "verify_semantic_scholar_citation"]
