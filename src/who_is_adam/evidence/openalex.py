"""OpenAlex fallback client for citation metadata verification."""

from __future__ import annotations

import httpx

from who_is_adam.config import ReviewConfig
from who_is_adam.models import ProviderEvidence, ProviderStatus, ReferenceEntry

from .citations import (
    ProviderRequestBudget,
    ProviderResult,
    classify_reference_match,
    make_provider_http_client,
    select_best_candidate,
)


class OpenAlexClient:
    def __init__(
        self,
        config: ReviewConfig,
        *,
        client: httpx.Client | None = None,
        request_budget: ProviderRequestBudget | None = None,
    ) -> None:
        self.http = make_provider_http_client(
            "openalex",
            config.openalex,
            offline=config.offline,
            client=client,
            request_budget=request_budget,
        )

    def close(self) -> None:
        self.http.close()

    def verify(self, reference: ReferenceEntry) -> ProviderEvidence:
        if not reference.title:
            return ProviderResult(
                "openalex", ProviderStatus.UNAVAILABLE, "reference has no parsed title"
            ).evidence()
        data, error = self.http.get_json("works", params={"search": reference.title, "per-page": 5})
        if error:
            return error.evidence()
        results = (data or {}).get("results")
        if not isinstance(results, list) or not results:
            return ProviderResult(
                "openalex", ProviderStatus.NOT_FOUND, "no OpenAlex work found"
            ).evidence()
        candidates = [result for result in results if isinstance(result, dict)]
        candidate = select_best_candidate(reference, candidates)
        if candidate is None:
            return ProviderResult(
                "openalex",
                ProviderStatus.NOT_FOUND,
                "no OpenAlex candidate met the title threshold",
            ).evidence()
        result = classify_reference_match(reference, candidate)
        raw_url = candidate.get("id")
        url = raw_url if isinstance(raw_url, str) else None
        return ProviderResult(
            "openalex", result.status, result.diagnostic, url, result.metadata
        ).evidence()


def verify_openalex_citation(
    reference: ReferenceEntry,
    config: ReviewConfig,
    *,
    client: httpx.Client | None = None,
    request_budget: ProviderRequestBudget | None = None,
) -> ProviderEvidence:
    provider = OpenAlexClient(config, client=client, request_budget=request_budget)
    try:
        return provider.verify(reference)
    finally:
        provider.close()


__all__ = ["OpenAlexClient", "verify_openalex_citation"]
