"""Citation matching helpers and shared HTTP provider primitives."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import sleep
from typing import Any

import httpx
from rapidfuzz import fuzz

from who_is_adam.config import HttpProviderConfig, ReviewConfig
from who_is_adam.models import CitationCheck, CitationStatus, ProviderEvidence, ProviderStatus, ReferenceEntry

Json = Mapping[str, Any]


@dataclass(frozen=True)
class ProviderResult:
    """Normalized external evidence result."""

    provider: str
    status: ProviderStatus
    diagnostic: str | None = None
    url: str | None = None
    metadata: dict[str, str | int | float | bool | None] | None = None

    def evidence(self) -> ProviderEvidence:
        return ProviderEvidence(
            provider=self.provider,
            status=self.status,
            diagnostic=self.diagnostic,
            url=self.url,
            metadata=self.metadata or {},
        )


class OfflineClient:
    """httpx-compatible client that fails closed instead of touching the network."""

    def get(self, url: str, **_: Any) -> httpx.Response:
        raise httpx.RequestError("network disabled by offline provider", request=httpx.Request("GET", url))


class ProviderHttpClient:
    """Small injectable GET client with deterministic retry/error semantics."""

    def __init__(
        self,
        *,
        provider: str,
        config: HttpProviderConfig,
        offline: bool = False,
        client: httpx.Client | None = None,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self.provider = provider
        self.config = config
        self.offline = offline
        self._client = client or (OfflineClient() if offline else httpx.Client(timeout=_timeout(config)))
        self._sleeper = sleeper

    @property
    def base_url(self) -> str:
        return str(self.config.base_url).rstrip("/")

    def get_json(self, path: str = "", *, params: Mapping[str, Any] | None = None) -> tuple[Json | None, ProviderResult | None]:
        if self.offline:
            return None, ProviderResult(self.provider, ProviderStatus.UNAVAILABLE, "provider disabled in offline mode")
        url = f"{self.base_url}/{path.lstrip('/')}" if path else self.base_url
        headers = {"User-Agent": "who-is-adam/0.1 citation-verifier"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        attempts = self.config.max_retries + 1
        for attempt in range(attempts):
            try:
                response = self._client.get(url, params=params, headers=headers)
            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError, httpx.RequestError) as exc:
                if attempt + 1 < attempts:
                    self._sleeper(0.1 * (2**attempt))
                    continue
                return None, ProviderResult(self.provider, ProviderStatus.UNAVAILABLE, type(exc).__name__)
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt + 1 < attempts:
                    self._sleeper(0.1 * (2**attempt))
                    continue
                return None, ProviderResult(self.provider, ProviderStatus.UNAVAILABLE, f"HTTP {response.status_code}", str(response.url))
            if 400 <= response.status_code <= 499:
                return None, ProviderResult(self.provider, ProviderStatus.ERROR, f"HTTP {response.status_code}", str(response.url))
            try:
                data = response.json()
            except ValueError:
                return None, ProviderResult(self.provider, ProviderStatus.ERROR, "invalid JSON response", str(response.url))
            if not isinstance(data, Mapping):
                return None, ProviderResult(self.provider, ProviderStatus.ERROR, "JSON response was not an object", str(response.url))
            return data, None
        return None, ProviderResult(self.provider, ProviderStatus.UNAVAILABLE, "retry attempts exhausted")


def make_provider_http_client(
    provider: str,
    config: HttpProviderConfig,
    *,
    offline: bool = False,
    client: httpx.Client | None = None,
    sleeper: Callable[[float], None] = sleep,
) -> ProviderHttpClient:
    return ProviderHttpClient(provider=provider, config=config, offline=offline, client=client, sleeper=sleeper)


def classify_reference_match(reference: ReferenceEntry, candidate: Mapping[str, Any]) -> ProviderResult:
    """Classify candidate metadata as verified/weak/not-found/error without judging paper claims."""
    title = _candidate_title(candidate)
    if not title:
        return ProviderResult("citation", ProviderStatus.METADATA_ERROR, "candidate is missing a title")
    if not reference.title:
        return ProviderResult("citation", ProviderStatus.WEAK_MATCH, "reference has no parsed title", metadata={"matched_title": title})
    score = fuzz.token_set_ratio(_normalize(reference.title), _normalize(title))
    year_ok = _year(candidate) is None or reference.year is None or _year(candidate) == reference.year
    metadata: dict[str, str | int | float | bool | None] = {"matched_title": title, "title_score": float(score), "year_match": year_ok}
    if score >= 92 and year_ok:
        return ProviderResult("citation", ProviderStatus.VERIFIED, metadata=metadata)
    if score >= 75:
        return ProviderResult("citation", ProviderStatus.WEAK_MATCH, "title/year metadata only weakly matched", metadata=metadata)
    return ProviderResult("citation", ProviderStatus.NOT_FOUND, "candidate did not match reference title", metadata=metadata)


def combine_citation_status(check: CitationCheck) -> CitationStatus:
    statuses = [e.status for e in (check.crossref, check.semantic_scholar, check.arxiv) if e is not None]
    if ProviderStatus.VERIFIED in statuses:
        return CitationStatus.VERIFIED
    if ProviderStatus.WEAK_MATCH in statuses:
        return CitationStatus.WEAK_MATCH
    if ProviderStatus.METADATA_ERROR in statuses or ProviderStatus.ERROR in statuses:
        return CitationStatus.METADATA_ERROR
    if ProviderStatus.NOT_FOUND in statuses:
        return CitationStatus.NOT_FOUND
    return CitationStatus.UNAVAILABLE


def unavailable_provider(provider: str, diagnostic: str = "provider unavailable") -> ProviderEvidence:
    return ProviderResult(provider, ProviderStatus.UNAVAILABLE, diagnostic).evidence()


def offline_enabled(config: ReviewConfig) -> bool:
    return bool(config.offline)


def _timeout(config: HttpProviderConfig) -> httpx.Timeout:
    total = float(config.timeout_seconds)
    return httpx.Timeout(timeout=total, connect=min(5.0, total), read=min(20.0, total), write=total, pool=total)


def _candidate_title(candidate: Mapping[str, Any]) -> str | None:
    title = candidate.get("title")
    if isinstance(title, str):
        return title
    if isinstance(title, list) and title and isinstance(title[0], str):
        return title[0]
    return None


def _year(candidate: Mapping[str, Any]) -> int | None:
    for key in ("year", "publicationYear"):
        value = candidate.get(key)
        if isinstance(value, int):
            return value
    issued = candidate.get("issued")
    if isinstance(issued, Mapping):
        parts = issued.get("date-parts")
        if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0] and isinstance(parts[0][0], int):
            return parts[0][0]
    return None


def _normalize(value: str) -> str:
    return " ".join(value.casefold().strip().split())
