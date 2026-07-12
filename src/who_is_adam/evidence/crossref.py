"""Crossref citation fact verification client."""

from __future__ import annotations

import httpx

from who_is_adam.config import ReviewConfig
from who_is_adam.models import ProviderEvidence, ProviderStatus, ReferenceEntry

from .citations import ProviderHttpClient, ProviderResult, classify_reference_match, make_provider_http_client


class CrossrefClient:
    def __init__(self, config: ReviewConfig, *, client: httpx.Client | None = None) -> None:
        self.config = config
        self.http = make_provider_http_client(
            "crossref", config.crossref, offline=config.offline, client=client
        )

    def verify(self, reference: ReferenceEntry) -> ProviderEvidence:
        if reference.doi:
            return self._work_by_doi(reference)
        if not reference.title:
            return ProviderResult("crossref", ProviderStatus.UNAVAILABLE, "reference has no DOI or title").evidence()
        params: dict[str, str | int] = {"query.title": reference.title, "rows": 1}
        if self.config.crossref_mailto:
            params["mailto"] = self.config.crossref_mailto
        data, error = self.http.get_json("works", params=params)
        if error:
            return error.evidence()
        items = (((data or {}).get("message") or {}).get("items") or [])
        if not items:
            return ProviderResult("crossref", ProviderStatus.NOT_FOUND, "no Crossref work found").evidence()
        candidate = items[0]
        if not isinstance(candidate, dict):
            return ProviderResult("crossref", ProviderStatus.METADATA_ERROR, "Crossref item was not an object").evidence()
        return self._classified(reference, candidate, url=candidate.get("URL") if isinstance(candidate.get("URL"), str) else None)

    def _work_by_doi(self, reference: ReferenceEntry) -> ProviderEvidence:
        data, error = self.http.get_json(f"works/{reference.doi}")
        if error:
            return error.evidence()
        candidate = (data or {}).get("message")
        if not isinstance(candidate, dict):
            return ProviderResult("crossref", ProviderStatus.METADATA_ERROR, "Crossref DOI response missing message").evidence()
        return self._classified(reference, candidate, url=candidate.get("URL") if isinstance(candidate.get("URL"), str) else None)

    @staticmethod
    def _classified(reference: ReferenceEntry, candidate: dict[str, object], *, url: str | None) -> ProviderEvidence:
        result = classify_reference_match(reference, candidate)
        return ProviderResult("crossref", result.status, result.diagnostic, url, result.metadata).evidence()


def verify_crossref_citation(
    reference: ReferenceEntry, config: ReviewConfig, *, client: httpx.Client | None = None
) -> ProviderEvidence:
    return CrossrefClient(config, client=client).verify(reference)


__all__ = ["CrossrefClient", "ProviderHttpClient", "verify_crossref_citation"]
