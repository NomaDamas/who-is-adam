"""arXiv citation fact verification client."""

from __future__ import annotations

from xml.etree import ElementTree

import httpx

from who_is_adam.config import ReviewConfig
from who_is_adam.models import ProviderEvidence, ProviderStatus, ReferenceEntry

from .citations import (
    ProviderRequestBudget,
    ProviderResult,
    classify_reference_match,
    make_provider_http_client,
)

ATOM = "{http://www.w3.org/2005/Atom}"


class ArxivClient:
    def __init__(
        self,
        config: ReviewConfig,
        *,
        client: httpx.Client | None = None,
        request_budget: ProviderRequestBudget | None = None,
    ) -> None:
        self.http = make_provider_http_client(
            "arxiv",
            config.arxiv,
            offline=config.offline,
            client=client,
            request_budget=request_budget,
        )

    def close(self) -> None:
        self.http.close()

    def verify(self, reference: ReferenceEntry) -> ProviderEvidence:
        if not reference.arxiv_id and not reference.title:
            return ProviderResult(
                "arxiv", ProviderStatus.UNAVAILABLE, "reference has no arXiv id or title"
            ).evidence()
        query = f"id:{reference.arxiv_id}" if reference.arxiv_id else f"ti:{reference.title}"
        if self.http.offline:
            return ProviderResult(
                "arxiv", ProviderStatus.UNAVAILABLE, "provider disabled in offline mode"
            ).evidence()
        response = self._get_atom(query)
        if isinstance(response, ProviderEvidence):
            return response
        try:
            root = ElementTree.fromstring(response.text)
        except ElementTree.ParseError:
            return ProviderResult(
                "arxiv", ProviderStatus.ERROR, "invalid arXiv Atom response", str(response.url)
            ).evidence()
        entry = root.find(f"{ATOM}entry")
        if entry is None:
            return ProviderResult(
                "arxiv", ProviderStatus.NOT_FOUND, "no arXiv entry found", str(response.url)
            ).evidence()
        title_el = entry.find(f"{ATOM}title")
        title = " ".join((title_el.text or "").split()) if title_el is not None else ""
        if not title:
            return ProviderResult(
                "arxiv",
                ProviderStatus.METADATA_ERROR,
                "arXiv entry missing title",
                str(response.url),
            ).evidence()
        entry_id = entry.find(f"{ATOM}id")
        url = entry_id.text if entry_id is not None and entry_id.text else str(response.url)
        authors = [
            " ".join((name.text or "").split())
            for author in entry.findall(f"{ATOM}author")
            if (name := author.find(f"{ATOM}name")) is not None and name.text
        ]
        published = entry.find(f"{ATOM}published")
        year = (
            int(published.text[:4])
            if published is not None and published.text and published.text[:4].isdigit()
            else None
        )
        arxiv_id = url.rstrip("/").split("/")[-1].split("v", 1)[0]
        result = classify_reference_match(
            reference,
            {
                "title": title,
                "authors": authors,
                "year": year,
                "arxiv_id": arxiv_id,
            },
        )
        return ProviderResult(
            "arxiv", result.status, result.diagnostic, url, result.metadata
        ).evidence()

    def _get_atom(self, query: str) -> httpx.Response | ProviderEvidence:
        attempts = self.http.config.max_retries + 1
        for attempt in range(attempts):
            if not self.http.consume_request():
                return ProviderResult(
                    "arxiv", ProviderStatus.UNAVAILABLE, "provider request budget exhausted"
                ).evidence()
            try:
                response = self.http._client.get(
                    self.http.base_url,
                    params={"search_query": query, "start": 0, "max_results": 1},
                    headers={"User-Agent": "who-is-adam/0.1 citation-verifier"},
                )
            except httpx.RequestError as exc:
                if attempt + 1 < attempts:
                    self.http._sleeper(0.1 * (2**attempt))
                    continue
                return ProviderResult(
                    "arxiv", ProviderStatus.UNAVAILABLE, type(exc).__name__
                ).evidence()
            if response.status_code == 429 or response.status_code >= 500:
                if attempt + 1 < attempts:
                    self.http._sleeper(0.1 * (2**attempt))
                    continue
                return ProviderResult(
                    "arxiv",
                    ProviderStatus.UNAVAILABLE,
                    f"HTTP {response.status_code}",
                    str(response.url),
                ).evidence()
            if response.status_code >= 400:
                return ProviderResult(
                    "arxiv",
                    ProviderStatus.UNAVAILABLE,
                    f"HTTP {response.status_code}",
                    str(response.url),
                ).evidence()
            return response
        return ProviderResult(
            "arxiv", ProviderStatus.UNAVAILABLE, "retry attempts exhausted"
        ).evidence()


def verify_arxiv_citation(
    reference: ReferenceEntry,
    config: ReviewConfig,
    *,
    client: httpx.Client | None = None,
    request_budget: ProviderRequestBudget | None = None,
) -> ProviderEvidence:
    provider = ArxivClient(config, client=client, request_budget=request_budget)
    try:
        return provider.verify(reference)
    finally:
        provider.close()


__all__ = ["ArxivClient", "verify_arxiv_citation"]
