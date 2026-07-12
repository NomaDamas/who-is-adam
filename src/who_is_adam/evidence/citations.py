"""Citation matching helpers and shared HTTP provider primitives."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import sleep
from typing import Any

import httpx
from who_is_adam.config import HttpProviderConfig, ReviewConfig
from who_is_adam.models import (
    CitationCheck,
    CitationStatus,
    ProviderEvidence,
    ProviderStatus,
    ReferenceEntry,
)

from .citation_consensus import provider_metadata_agree
from .citation_matching import match_reference, select_best_candidate

Json = Mapping[str, Any]


class ProviderRequestBudget:
    """Mutable shared counter for actual outbound citation-provider requests."""

    __slots__ = ("remaining",)

    def __init__(self, *, remaining: int) -> None:
        self.remaining = remaining

    def consume(self) -> bool:
        if self.remaining <= 0:
            return False
        self.remaining -= 1
        return True


@dataclass(frozen=True, slots=True)
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
        raise httpx.RequestError(
            "network disabled by offline provider", request=httpx.Request("GET", url)
        )


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
        request_budget: ProviderRequestBudget | None = None,
    ) -> None:
        self.provider = provider
        self.config = config
        self.offline = offline
        self._owns_client = client is None
        self._client = client or (
            OfflineClient() if offline else httpx.Client(timeout=_timeout(config))
        )
        self._sleeper = sleeper
        self._request_budget = request_budget

    @property
    def base_url(self) -> str:
        return str(self.config.base_url).rstrip("/")

    def close(self) -> None:
        if self._owns_client and isinstance(self._client, httpx.Client):
            self._client.close()

    def consume_request(self) -> bool:
        return self._request_budget is None or self._request_budget.consume()

    def get_json(
        self, path: str = "", *, params: Mapping[str, Any] | None = None
    ) -> tuple[Json | None, ProviderResult | None]:
        if self.offline:
            return None, ProviderResult(
                self.provider, ProviderStatus.UNAVAILABLE, "provider disabled in offline mode"
            )
        url = f"{self.base_url}/{path.lstrip('/')}" if path else self.base_url
        headers = {"User-Agent": "who-is-adam/0.1 citation-verifier"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        attempts = self.config.max_retries + 1
        for attempt in range(attempts):
            if not self.consume_request():
                return None, ProviderResult(
                    self.provider,
                    ProviderStatus.UNAVAILABLE,
                    "provider request budget exhausted",
                )
            try:
                response = self._client.get(url, params=params, headers=headers)
            except (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.NetworkError,
                httpx.RequestError,
            ) as exc:
                if attempt + 1 < attempts:
                    self._sleeper(0.1 * (2**attempt))
                    continue
                return None, ProviderResult(
                    self.provider, ProviderStatus.UNAVAILABLE, type(exc).__name__
                )
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt + 1 < attempts:
                    self._sleeper(0.1 * (2**attempt))
                    continue
                return None, ProviderResult(
                    self.provider,
                    ProviderStatus.UNAVAILABLE,
                    f"HTTP {response.status_code}",
                    str(response.url),
                )
            if 400 <= response.status_code <= 499:
                return None, ProviderResult(
                    self.provider,
                    ProviderStatus.UNAVAILABLE,
                    f"HTTP {response.status_code}",
                    str(response.url),
                )
            try:
                data = response.json()
            except ValueError:
                return None, ProviderResult(
                    self.provider, ProviderStatus.ERROR, "invalid JSON response", str(response.url)
                )
            if not isinstance(data, Mapping):
                return None, ProviderResult(
                    self.provider,
                    ProviderStatus.ERROR,
                    "JSON response was not an object",
                    str(response.url),
                )
            return data, None
        return None, ProviderResult(
            self.provider, ProviderStatus.UNAVAILABLE, "retry attempts exhausted"
        )


def make_provider_http_client(
    provider: str,
    config: HttpProviderConfig,
    *,
    offline: bool = False,
    client: httpx.Client | None = None,
    sleeper: Callable[[float], None] = sleep,
    request_budget: ProviderRequestBudget | None = None,
) -> ProviderHttpClient:
    return ProviderHttpClient(
        provider=provider,
        config=config,
        offline=offline,
        client=client,
        sleeper=sleeper,
        request_budget=request_budget,
    )


def classify_reference_match(
    reference: ReferenceEntry, candidate: Mapping[str, Any]
) -> ProviderResult:
    """Classify candidate metadata without allowing title-only false verification."""
    result = match_reference(reference, candidate)
    return ProviderResult("citation", result.status, result.diagnostic, metadata=result.metadata)


def combine_citation_status(check: CitationCheck) -> CitationStatus:
    statuses = [
        evidence.status
        for evidence in (check.crossref, check.semantic_scholar, check.openalex, check.arxiv)
        if evidence is not None
    ]
    available = [status for status in statuses if status is not ProviderStatus.UNAVAILABLE]
    verified = [
        evidence
        for evidence in (check.crossref, check.semantic_scholar, check.openalex, check.arxiv)
        if evidence is not None and evidence.status is ProviderStatus.VERIFIED
    ]
    if any(
        not provider_metadata_agree(left.metadata, right.metadata)
        for index, left in enumerate(verified)
        for right in verified[index + 1 :]
    ):
        return CitationStatus.NEEDS_REVIEW
    if ProviderStatus.NEEDS_REVIEW in available:
        return CitationStatus.NEEDS_REVIEW
    if ProviderStatus.VERIFIED in available and any(
        status in {ProviderStatus.NOT_FOUND, ProviderStatus.METADATA_ERROR, ProviderStatus.ERROR}
        for status in available
    ):
        return CitationStatus.NEEDS_REVIEW
    if ProviderStatus.VERIFIED in available:
        return CitationStatus.VERIFIED
    if ProviderStatus.WEAK_MATCH in available:
        return CitationStatus.WEAK_MATCH
    if ProviderStatus.METADATA_ERROR in available or ProviderStatus.ERROR in available:
        return CitationStatus.METADATA_ERROR
    if ProviderStatus.NOT_FOUND in available:
        return CitationStatus.NOT_FOUND
    return CitationStatus.UNAVAILABLE


def unavailable_provider(
    provider: str, diagnostic: str = "provider unavailable"
) -> ProviderEvidence:
    return ProviderResult(provider, ProviderStatus.UNAVAILABLE, diagnostic).evidence()


def identifier_fallback_evidence(
    evidence: ProviderEvidence,
    identifier: str,
    metadata_key: str,
) -> ProviderEvidence:
    """Require review when search fallback does not reconfirm the failed identifier."""
    if evidence.status is not ProviderStatus.VERIFIED:
        return evidence
    if evidence.metadata.get(metadata_key) is True:
        return evidence
    return evidence.model_copy(
        update={
            "status": ProviderStatus.NEEDS_REVIEW,
            "diagnostic": f"exact {identifier} lookup failed; title fallback did not confirm identifier",
        }
    )


def offline_enabled(config: ReviewConfig) -> bool:
    return bool(config.offline)


def _timeout(config: HttpProviderConfig) -> httpx.Timeout:
    total = float(config.timeout_seconds)
    return httpx.Timeout(
        timeout=total, connect=min(5.0, total), read=min(20.0, total), write=total, pool=total
    )


__all__ = [
    "OfflineClient",
    "ProviderHttpClient",
    "ProviderRequestBudget",
    "ProviderResult",
    "classify_reference_match",
    "combine_citation_status",
    "identifier_fallback_evidence",
    "make_provider_http_client",
    "select_best_candidate",
]
