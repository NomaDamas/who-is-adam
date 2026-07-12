"""Crossref citation fact verification client."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

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


class CrossrefClient:
    def __init__(
        self,
        config: ReviewConfig,
        *,
        client: httpx.Client | None = None,
        request_budget: ProviderRequestBudget | None = None,
    ) -> None:
        self.config = config
        self.http = make_provider_http_client(
            "crossref",
            config.crossref,
            offline=config.offline,
            client=client,
            request_budget=request_budget,
        )

    def close(self) -> None:
        self.http.close()

    def verify(self, reference: ReferenceEntry) -> ProviderEvidence:
        if reference.doi:
            exact = self._work_by_doi(reference)
            if exact.diagnostic != "HTTP 404":
                return exact
        if not reference.title:
            return ProviderResult(
                "crossref", ProviderStatus.UNAVAILABLE, "reference has no DOI or title"
            ).evidence()
        fallback = self._search_by_title(reference)
        return (
            identifier_fallback_evidence(fallback, "DOI", "doi_match")
            if reference.doi
            else fallback
        )

    def _search_by_title(self, reference: ReferenceEntry) -> ProviderEvidence:
        assert reference.title is not None
        params: dict[str, str | int] = {"query.title": reference.title, "rows": 5}
        if self.config.crossref_mailto:
            params["mailto"] = self.config.crossref_mailto
        data, error = self.http.get_json("works", params=params)
        if error:
            return error.evidence()
        items = ((data or {}).get("message") or {}).get("items") or []
        if not items:
            return ProviderResult(
                "crossref", ProviderStatus.NOT_FOUND, "no Crossref work found"
            ).evidence()
        candidates = [item for item in items if isinstance(item, dict)]
        candidate = select_best_candidate(reference, candidates)
        if candidate is None:
            return ProviderResult(
                "crossref",
                ProviderStatus.NOT_FOUND,
                "no Crossref candidate met the title threshold",
            ).evidence()
        return self._classified(
            reference,
            candidate,
            url=candidate.get("URL") if isinstance(candidate.get("URL"), str) else None,
        )

    def _work_by_doi(self, reference: ReferenceEntry) -> ProviderEvidence:
        data, error = self.http.get_json(f"works/{reference.doi}")
        if error:
            return error.evidence()
        candidate = (data or {}).get("message")
        if not isinstance(candidate, dict):
            return ProviderResult(
                "crossref", ProviderStatus.METADATA_ERROR, "Crossref DOI response missing message"
            ).evidence()
        return self._classified(
            reference,
            candidate,
            url=candidate.get("URL") if isinstance(candidate.get("URL"), str) else None,
        )

    @staticmethod
    def _classified(
        reference: ReferenceEntry,
        candidate: Mapping[str, Any],
        *,
        url: str | None,
    ) -> ProviderEvidence:
        result = classify_reference_match(reference, candidate)
        return ProviderResult(
            "crossref", result.status, result.diagnostic, url, result.metadata
        ).evidence()


def verify_crossref_citation(
    reference: ReferenceEntry,
    config: ReviewConfig,
    *,
    client: httpx.Client | None = None,
    request_budget: ProviderRequestBudget | None = None,
) -> ProviderEvidence:
    provider = CrossrefClient(config, client=client, request_budget=request_budget)
    try:
        return provider.verify(reference)
    finally:
        provider.close()


__all__ = ["CrossrefClient", "ProviderHttpClient", "verify_crossref_citation"]
