"""LLM provider contracts and deterministic test implementation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, TypeAdapter, ValidationError

from who_is_adam.models import EvidenceSpan, Finding, ReviewScores, SpecialistReview, SynthesizedReview

JsonObject = dict[str, Any]
SchemaType = type[BaseModel] | TypeAdapter[Any] | Mapping[str, Any]
T = TypeVar("T", bound=BaseModel)


class LlmClient(Protocol):
    """Protocol for providers that can return schema-constrained JSON."""

    def complete_json(
        self,
        prompt: str,
        schema: SchemaType,
        safety_context: Mapping[str, str] | None = None,
    ) -> JsonObject:
        """Return JSON constrained by ``schema`` or raise a provider/config error."""


class FakeLlmClient:
    """Deterministic offline LLM client for tests and local contract checks."""

    def __init__(self, responses: Mapping[str, JsonObject] | None = None) -> None:
        self._responses = dict(responses or {})

    def complete_json(
        self,
        prompt: str,
        schema: SchemaType,
        safety_context: Mapping[str, str] | None = None,
    ) -> JsonObject:
        del safety_context
        payload = self._responses.get(_role_key(prompt))
        if payload is None:
            payload = _default_payload_for_schema(schema, role=_role_key(prompt))
        return _validate_payload(payload, schema)


def _role_key(prompt: str) -> str:
    first_line = prompt.splitlines()[0].strip().lower() if prompt.splitlines() else ""
    if first_line.startswith("role:"):
        return first_line.removeprefix("role:").strip()
    return "default"


def _validate_payload(payload: JsonObject, schema: SchemaType) -> JsonObject:
    if isinstance(schema, TypeAdapter):
        validated = schema.validate_python(payload)
        return _dump_validated(validated)
    if isinstance(schema, type) and issubclass(schema, BaseModel):
        validated_model = schema.model_validate(payload)
        return validated_model.model_dump(mode="json")
    # Raw JSON schema mappings are accepted as a provider capability contract. The
    # fake still returns a copied dict so callers cannot mutate canned responses.
    return dict(payload)


def _dump_validated(value: Any) -> JsonObject:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return dict(value)
    raise TypeError("schema-constrained fake response must validate to a JSON object")



def _default_payload_for_schema(schema: SchemaType, *, role: str) -> JsonObject:
    if isinstance(schema, type) and issubclass(schema, SpecialistReview):
        return _default_specialist_review_payload(role)
    if isinstance(schema, type) and issubclass(schema, SynthesizedReview):
        return _default_review_payload()
    for payload in (_default_specialist_review_payload(role), _default_review_payload()):
        if _payload_validates(payload, schema):
            return payload
    return _default_review_payload()


def _payload_validates(payload: JsonObject, schema: SchemaType) -> bool:
    try:
        _validate_payload(payload, schema)
    except (TypeError, ValueError, ValidationError):
        return False
    return True


def _default_specialist_review_payload(role: str) -> JsonObject:
    evidence = EvidenceSpan(page=1, section="Abstract", text="Deterministic offline evidence.")
    review = SpecialistReview(
        role=role if role != "default" else "methodology",
        findings=[
            Finding(
                claim="Deterministic specialist finding cites extracted paper evidence.",
                evidence=[evidence],
            )
        ],
        scores=ReviewScores(
            soundness=3,
            presentation=3,
            significance=3,
            originality=3,
            overall_recommendation=4,
            confidence=3,
        ),
        evidence=[evidence],
        uncertainty="Offline fake specialist review is for contract testing only.",
    )
    return review.model_dump(mode="json")

def _default_review_payload() -> JsonObject:
    evidence = EvidenceSpan(page=1, section="Abstract", text="Deterministic offline evidence.")
    review = SynthesizedReview(
        summary="Deterministic offline summary.",
        strengths=["Clear motivation is stated."],
        weaknesses=["Empirical support remains limited."],
        questions=["Which ablations are most critical?"],
        limitations=["Offline fake review is for contract testing only."],
        soundness=3,
        presentation=3,
        significance=3,
        originality=3,
        overall_recommendation=4,
        confidence=3,
        ethical_concerns="No specific ethical concern is identified in the fake response.",
        reproducibility_notes="Reproducibility cannot be assessed by the fake client.",
        evidence=[evidence],
        consensus=["Specialists agree evidence is required."],
        conflicts=[],
        minority_opinions=[],
    )
    return review.model_dump(mode="json")
