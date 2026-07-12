from __future__ import annotations

import httpx


from who_is_adam.config import ReviewConfig
from who_is_adam.evidence.arxiv import verify_arxiv_citation
from who_is_adam.evidence.citations import combine_citation_status
from who_is_adam.evidence.crossref import verify_crossref_citation
from who_is_adam.evidence.semantic_scholar import verify_semantic_scholar_citation
from who_is_adam.models import CitationCheck, CitationStatus, ProviderStatus, ReferenceEntry


def test_offline_citation_providers_fail_closed_without_network() -> None:
    config = ReviewConfig(offline=True)
    reference = ReferenceEntry(
        raw="Smith 2024 Deterministic Citation Checking. arXiv:2401.00001. doi:10.1234/example",
        title="Deterministic Citation Checking",
        year=2024,
        doi="10.1234/example",
        arxiv_id="2401.00001",
    )

    crossref = verify_crossref_citation(reference, config)
    semantic_scholar = verify_semantic_scholar_citation(reference, config)
    arxiv = verify_arxiv_citation(reference, config)

    assert [crossref.status, semantic_scholar.status, arxiv.status] == [
        ProviderStatus.UNAVAILABLE,
        ProviderStatus.UNAVAILABLE,
        ProviderStatus.UNAVAILABLE,
    ]
    assert combine_citation_status(
        CitationCheck(reference=reference, crossref=crossref, semantic_scholar=semantic_scholar, arxiv=arxiv, status=CitationStatus.UNAVAILABLE)
    ) is CitationStatus.UNAVAILABLE



def test_static_provider_payloads_produce_verified_no_live_network() -> None:
    config = ReviewConfig()
    reference = ReferenceEntry(
        raw="Smith 2024 Deterministic Citation Checking. arXiv:2401.00001. doi:10.1234/example",
        title="Deterministic Citation Checking",
        year=2024,
        doi="10.1234/example",
        arxiv_id="2401.00001",
    )
    call_counts = {"crossref": 0, "semantic_scholar": 0, "arxiv": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        if request.url.host == "api.crossref.org":
            call_counts["crossref"] += 1
            assert request.url.path == "/works/10.1234/example"
            assert request.url.query == b""
            return httpx.Response(
                200,
                json={"message": {"title": ["Deterministic Citation Checking"], "year": 2024, "URL": "https://doi.org/10.1234/example"}},
            )
        if request.url.host == "api.semanticscholar.org":
            call_counts["semantic_scholar"] += 1
            assert request.url.path == "/graph/v1/paper/DOI:10.1234/example"
            assert dict(request.url.params) == {"fields": "title,year,url,externalIds"}
            return httpx.Response(
                200,
                json={"title": "Deterministic Citation Checking", "year": 2024, "url": "https://semanticscholar.org/paper/example"},
            )
        if request.url.host == "export.arxiv.org":
            call_counts["arxiv"] += 1
            assert request.url.path == "/api/query"
            assert dict(request.url.params) == {"search_query": "id:2401.00001", "start": "0", "max_results": "1"}
            return httpx.Response(
                200,
                text="""<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'><entry><id>https://arxiv.org/abs/2401.00001</id><title>Deterministic Citation Checking</title></entry></feed>""",
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        crossref = verify_crossref_citation(reference, config, client=client)
        semantic_scholar = verify_semantic_scholar_citation(reference, config, client=client)
        arxiv = verify_arxiv_citation(reference, config, client=client)

    assert call_counts == {"crossref": 1, "semantic_scholar": 1, "arxiv": 1}

    assert crossref.status is ProviderStatus.VERIFIED
    assert semantic_scholar.status is ProviderStatus.VERIFIED
    assert arxiv.status is ProviderStatus.VERIFIED
    assert combine_citation_status(
        CitationCheck(reference=reference, crossref=crossref, semantic_scholar=semantic_scholar, arxiv=arxiv, status=CitationStatus.VERIFIED)
    ) is CitationStatus.VERIFIED
