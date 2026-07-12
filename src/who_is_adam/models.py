"""Pydantic contracts for ICML review runs."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, model_validator


class GateStatus(StrEnum):
    PASS = "pass"
    REJECT = "reject"
    WARN = "warn"


class CheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    UNKNOWN = "unknown"


class CitationStatus(StrEnum):
    VERIFIED = "verified"
    WEAK_MATCH = "weak_match"
    NOT_FOUND = "not_found"
    METADATA_ERROR = "metadata_error"
    UNAVAILABLE = "unavailable"


class PriorWorkComparison(StrEnum):
    IMPROVED = "improved"
    MAINTAINED = "maintained"
    WORSENED = "worsened"
    UNAVAILABLE = "unavailable"


class ReviewRunStatus(StrEnum):
    SAVED = "saved"
    REFUSED = "refused"


class ProviderStatus(StrEnum):
    VERIFIED = "verified"
    WEAK_MATCH = "weak_match"
    NOT_FOUND = "not_found"
    METADATA_ERROR = "metadata_error"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class EvidenceSpan(BaseModel):
    model_config = ConfigDict(frozen=True)

    page: int = Field(ge=1)
    section: str | None = None
    text: str = Field(min_length=1)
    char_start: NonNegativeInt | None = None
    char_end: NonNegativeInt | None = None

    @model_validator(mode="after")
    def validate_offsets(self) -> "EvidenceSpan":
        if self.char_start is not None and self.char_end is not None and self.char_end < self.char_start:
            raise ValueError("char_end must be greater than or equal to char_start")
        return self


class TableBlock(BaseModel):
    caption: str | None = None
    page: int = Field(ge=1)
    span: EvidenceSpan | None = None


class FigureBlock(BaseModel):
    caption: str | None = None
    page: int = Field(ge=1)
    span: EvidenceSpan | None = None


class FormulaBlock(BaseModel):
    label: str | None = None
    latex: str | None = None
    page: int = Field(ge=1)
    span: EvidenceSpan | None = None


class ReferenceEntry(BaseModel):
    raw: str = Field(min_length=1)
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = Field(default=None, ge=1800, le=2100)
    venue: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    span: EvidenceSpan | None = None


class SectionBlock(BaseModel):
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    spans: list[EvidenceSpan] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_pages(self) -> "SectionBlock":
        if self.page_end < self.page_start:
            raise ValueError("page_end must be greater than or equal to page_start")
        return self


class ExtractionMetrics(BaseModel):
    page_count: int = Field(ge=1)
    extracted_text_chars: NonNegativeInt = 0
    low_text_pages: list[int] = Field(default_factory=list)
    ocr_used: bool = False
    encrypted: bool = False


class PaperStructure(BaseModel):
    title: str = Field(min_length=1)
    abstract: str = Field(min_length=1)
    sections: list[SectionBlock] = Field(min_length=1)
    pages: list[str] = Field(min_length=1)
    tables: list[TableBlock] = Field(default_factory=list)
    figures: list[FigureBlock] = Field(default_factory=list)
    formulas: list[FormulaBlock] = Field(default_factory=list)
    references: list[ReferenceEntry] = Field(default_factory=list)
    extraction_metrics: ExtractionMetrics


class GateResult(BaseModel):
    status: GateStatus
    reasons: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSpan] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_requires_reason(self) -> "GateResult":
        if self.status is GateStatus.REJECT and not self.reasons:
            raise ValueError("rejected gates require at least one reason")
        return self


class DeskRejectCheck(BaseModel):
    rule_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    status: CheckStatus
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    diagnostic: str | None = None


class ProviderEvidence(BaseModel):
    provider: str = Field(min_length=1)
    status: ProviderStatus
    diagnostic: str | None = None
    url: str | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class CitationCheck(BaseModel):
    reference: ReferenceEntry
    crossref: ProviderEvidence | None = None
    semantic_scholar: ProviderEvidence | None = None
    arxiv: ProviderEvidence | None = None
    status: CitationStatus


class OpenReviewReviewAssessment(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    review_count: NonNegativeInt = 0


class PriorWorkEvidence(BaseModel):
    reference: ReferenceEntry
    claim_type: str = Field(min_length=1)
    paper_claim_span: EvidenceSpan
    openreview_evidence: ProviderEvidence | None = None
    openreview_review_assessment: OpenReviewReviewAssessment | None = None
    comparison: PriorWorkComparison

    @model_validator(mode="after")
    def unavailable_without_openreview_evidence(self) -> "PriorWorkEvidence":
        if self.openreview_evidence is None and self.comparison is not PriorWorkComparison.UNAVAILABLE:
            raise ValueError("prior-work comparison requires public OpenReview evidence")
        return self


class ReviewScores(BaseModel):
    soundness: int = Field(ge=1, le=4)
    presentation: int = Field(ge=1, le=4)
    significance: int = Field(ge=1, le=4)
    originality: int = Field(ge=1, le=4)
    overall_recommendation: int = Field(ge=1, le=6)
    confidence: int = Field(ge=1, le=5)


class Finding(BaseModel):
    claim: str = Field(min_length=1)
    evidence: list[EvidenceSpan] = Field(min_length=1)


class SpecialistReview(BaseModel):
    role: str = Field(min_length=1)
    findings: list[Finding] = Field(min_length=1)
    scores: ReviewScores
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    uncertainty: str | None = None


class SynthesizedReview(BaseModel):
    summary: str = Field(min_length=1)
    strengths: list[str] = Field(min_length=1)
    weaknesses: list[str] = Field(min_length=1)
    questions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    soundness: int = Field(ge=1, le=4)
    presentation: int = Field(ge=1, le=4)
    significance: int = Field(ge=1, le=4)
    originality: int = Field(ge=1, le=4)
    overall_recommendation: int = Field(ge=1, le=6)
    confidence: int = Field(ge=1, le=5)
    ethical_concerns: str = Field(min_length=1)
    reproducibility_notes: str = Field(min_length=1)
    evidence: list[EvidenceSpan] = Field(min_length=1)
    consensus: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    minority_opinions: list[str] = Field(default_factory=list)

    @property
    def scores(self) -> ReviewScores:
        return ReviewScores(
            soundness=self.soundness,
            presentation=self.presentation,
            significance=self.significance,
            originality=self.originality,
            overall_recommendation=self.overall_recommendation,
            confidence=self.confidence,
        )


class RuntimeMetadata(BaseModel):
    llm_policy_checked: bool
    llm_policy_name: str = Field(min_length=1)
    code_of_conduct_acknowledged: bool
    official_docs_checked_at: str = Field(min_length=1)
    provider_mode: str = Field(min_length=1)
    tool_versions: dict[str, str] = Field(default_factory=dict)
    fixed_run_timestamp: str | None = None
    random_seed: int = 0

    @model_validator(mode="after")
    def require_runtime_policy_metadata(self) -> "RuntimeMetadata":
        if not self.llm_policy_checked:
            raise ValueError("runtime metadata must confirm the assigned LLM policy was checked")
        if not self.code_of_conduct_acknowledged:
            raise ValueError("runtime metadata must confirm code-of-conduct acknowledgement")
        return self


class Refusal(BaseModel):
    reason: str = Field(min_length=1)
    diagnostics: list[GateResult | DeskRejectCheck] = Field(default_factory=list)


class ReviewRunResult(BaseModel):
    status: ReviewRunStatus
    output_path: Path | None = None
    refusal: Refusal | None = None
    metadata: RuntimeMetadata

    @model_validator(mode="after")
    def validate_status_payload(self) -> "ReviewRunResult":
        if self.status is ReviewRunStatus.SAVED and self.output_path is None:
            raise ValueError("saved review results require output_path")
        if self.status is ReviewRunStatus.REFUSED and self.refusal is None:
            raise ValueError("refused review results require refusal")
        return self
