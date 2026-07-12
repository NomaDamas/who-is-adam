from __future__ import annotations

import httpx


from who_is_adam.config import ReviewConfig
from who_is_adam.evidence.openreview import public_openreview_evidence
from who_is_adam.models import EvidenceSpan, PriorWorkComparison, PriorWorkEvidence, ProviderStatus, ReferenceEntry


def _reference(index: int) -> ReferenceEntry:
    return ReferenceEntry(raw=f"Author {index}. Prior Work {index}. ICLR 2024.", title=f"Prior Work {index}", year=2024)


def test_prior_work_selection_is_capped_at_five_by_static_policy() -> None:
    references = [_reference(index) for index in range(1, 8)]
    selected = [ref for ref in references if ref.title][:5]

    assert [ref.title for ref in selected] == [f"Prior Work {index}" for index in range(1, 6)]
    assert len(selected) == 5



def test_absent_openreview_public_evidence_is_unavailable_and_not_a_strength() -> None:
    config = ReviewConfig()
    reference = _reference(1)
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        assert request.method == "GET"
        assert request.url.host == "api2.openreview.net"
        assert request.url.path == "/notes"
        assert dict(request.url.params) == {"content.title": "Prior Work 1", "limit": "5"}
        return httpx.Response(200, json={"notes": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        evidence = public_openreview_evidence(reference, config, client=client)

    assert call_count == 1
    prior_work = PriorWorkEvidence(
        reference=reference,
        claim_type="claimed improvement",
        paper_claim_span=EvidenceSpan(page=2, section="Related Work", text="We improve over Prior Work 1."),
        openreview_evidence=evidence,
        comparison=PriorWorkComparison.UNAVAILABLE,
    )

    assert evidence.status is ProviderStatus.UNAVAILABLE
    assert prior_work.comparison is PriorWorkComparison.UNAVAILABLE
    assert "strength" not in (evidence.diagnostic or "").casefold()
