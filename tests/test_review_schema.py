from __future__ import annotations

import pytest
from pydantic import ValidationError

from who_is_adam.config import LlmConfig, LlmProvider, ProviderMode, ReviewConfig
from who_is_adam.llm.base import FakeLlmClient
from who_is_adam.models import EvidenceSpan, RuntimeMetadata, SynthesizedReview


def valid_review_payload() -> dict[str, object]:
    return {
        "summary": "A concise evidence-grounded summary.",
        "strengths": ["The paper states a clear problem."],
        "weaknesses": ["The evaluation is narrow."],
        "questions": ["How sensitive is the method to the seed?"],
        "limitations": ["Only the submitted evidence is considered."],
        "soundness": 3,
        "presentation": 3,
        "significance": 3,
        "originality": 3,
        "overall_recommendation": 4,
        "confidence": 3,
        "ethical_concerns": "No specific concern is identified from the provided evidence.",
        "reproducibility_notes": "Artifacts are not available in this skeleton test.",
        "evidence": [{"page": 1, "section": "Abstract", "text": "We propose a method."}],
        "consensus": ["Evidence must be cited."],
        "conflicts": [],
        "minority_opinions": [],
    }


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("soundness", 0),
        ("soundness", 5),
        ("presentation", 0),
        ("presentation", 5),
        ("significance", 0),
        ("significance", 5),
        ("originality", 0),
        ("originality", 5),
        ("overall_recommendation", 0),
        ("overall_recommendation", 7),
        ("confidence", 0),
        ("confidence", 6),
    ],
)
def test_official_icml_score_ranges_are_enforced(field: str, bad_value: int) -> None:
    payload = valid_review_payload()
    payload[field] = bad_value

    with pytest.raises(ValidationError):
        SynthesizedReview.model_validate(payload)


def test_required_official_review_sections_are_enforced() -> None:
    payload = valid_review_payload()
    del payload["weaknesses"]

    with pytest.raises(ValidationError):
        SynthesizedReview.model_validate(payload)


def test_runtime_metadata_requires_policy_and_code_of_conduct_ack() -> None:
    with pytest.raises(ValidationError):
        RuntimeMetadata(
            llm_policy_checked=True,
            llm_policy_name="assigned policy",
            code_of_conduct_acknowledged=False,
            official_docs_checked_at="2026-07-12",
            provider_mode="fake",
        )


def test_offline_config_forces_fake_provider() -> None:
    config = ReviewConfig(
        offline=True,
        llm=LlmConfig(
            provider=LlmProvider.OPENAI,
            model="model",
            api_key="key",
            supports_json_schema=True,
        ),
    )

    assert config.provider_mode is ProviderMode.OFFLINE
    assert config.llm.provider is LlmProvider.FAKE


def test_hosted_llm_requires_json_schema_capability() -> None:
    with pytest.raises(ValidationError, match="JSON-schema output support"):
        LlmConfig(
            provider=LlmProvider.OPENAI,
            model="model",
            api_key="key",
            supports_json_schema=False,
        )


def test_fake_llm_returns_schema_valid_deterministic_json() -> None:
    client = FakeLlmClient()

    first = client.complete_json("role: synthesis", SynthesizedReview)
    second = client.complete_json("role: synthesis", SynthesizedReview)

    assert first == second
    validated = SynthesizedReview.model_validate(first)
    assert validated.scores.overall_recommendation == 4
    assert validated.evidence == [
        EvidenceSpan(page=1, section="Abstract", text="Deterministic offline evidence.")
    ]
