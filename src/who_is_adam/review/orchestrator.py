"""End-to-end ICML review orchestration."""

from __future__ import annotations

from pathlib import Path

from who_is_adam.config import LlmProvider, ReviewConfig
from who_is_adam.evidence.prior_work import compare_prior_work_with_openreview
from who_is_adam.icml.desk_reject import blocking_checks, run_desk_reject_checks
from who_is_adam.llm.base import FakeLlmClient, LlmClient
from who_is_adam.models import GateResult, GateStatus, Refusal, ReviewRunResult, ReviewRunStatus, RuntimeMetadata
from who_is_adam.output.markdown import render_review_markdown
from who_is_adam.output.paths import persist_markdown_atomic
from who_is_adam.pdf.extractor import PdfExtractionError, PdfExtractor
from who_is_adam.pdf.ocr import NullOcrAdapter, TesseractOcrAdapter
from who_is_adam.review.deliberation import run_review_deliberation
from who_is_adam.review.specialists import run_specialist_reviews
from who_is_adam.review.synthesis import synthesize_reviews
from who_is_adam.safety.quality_gate import evaluate_pre_review_gates

MAX_PDF_BYTES = 50 * 1024 * 1024


class ReviewOrchestrationError(RuntimeError):
    """Raised when the configured review run cannot be completed."""


def run_review(
    *,
    pdf_path: Path,
    output_dir: Path,
    llm_policy: str,
    code_of_conduct_acknowledged: bool,
    config: ReviewConfig,
    supplementary_pdf_path: Path | None = None,
    llm_client: LlmClient | None = None,
) -> ReviewRunResult:
    """Run extraction, hard safety gates, evidence checks, review generation, and persistence."""

    metadata = RuntimeMetadata(
        llm_policy_checked=bool(llm_policy.strip()),
        llm_policy_name=llm_policy.strip() or "missing",
        code_of_conduct_acknowledged=code_of_conduct_acknowledged,
        official_docs_checked_at=config.fixed_run_timestamp or "runtime-static-icml-main-track",
        provider_mode=str(config.provider_mode),
        tool_versions={},
        fixed_run_timestamp=config.fixed_run_timestamp,
        random_seed=config.random_seed,
    )
    input_refusal = _input_refusal(pdf_path)
    if input_refusal is not None:
        return ReviewRunResult(
            status=ReviewRunStatus.REFUSED,
            refusal=input_refusal,
            metadata=metadata,
        )

    extractor = _pdf_extractor(config)
    try:
        paper = extractor.extract(pdf_path)
    except PdfExtractionError as exc:
        return ReviewRunResult(
            status=ReviewRunStatus.REFUSED,
            refusal=Refusal(
                reason="PDF extraction failed before review generation",
                diagnostics=[GateResult(status=GateStatus.REJECT, reasons=[f"pdf_extraction_error: {exc}"])],
            ),
            metadata=metadata,
        )
    gate = evaluate_pre_review_gates(paper)
    if gate.status is GateStatus.REJECT:
        return ReviewRunResult(
            status=ReviewRunStatus.REFUSED,
            refusal=Refusal(reason="pre-review quality or prompt-injection gate rejected the PDF", diagnostics=[gate]),
            metadata=metadata,
        )

    desk_checks = run_desk_reject_checks(paper, supplementary_provided=supplementary_pdf_path is not None)
    blockers = blocking_checks(desk_checks)
    if blockers:
        return ReviewRunResult(
            status=ReviewRunStatus.REFUSED,
            refusal=Refusal(reason="ICML Main Track desk-reject check failed", diagnostics=list(blockers)),
            metadata=metadata,
        )

    client = llm_client or _llm_client(config)
    specialist_reviews = run_specialist_reviews(paper=paper, llm_client=client)
    deliberation = run_review_deliberation(specialist_reviews=specialist_reviews, llm_client=client)
    synthesized = synthesize_reviews(
        specialist_reviews=specialist_reviews,
        llm_client=client,
        deliberation=deliberation,
    )
    prior_work = compare_prior_work_with_openreview(paper, config)

    markdown = render_review_markdown(
        synthesized,
        metadata=metadata,
        appendices={
            "icml_track": "main",
            "desk_reject_checks": [check.model_dump(mode="json") for check in desk_checks],
            "review_deliberation": deliberation.model_dump(mode="json"),
            "prior_work_comparisons": [item.model_dump(mode="json") for item in prior_work],
        },
    )
    output_path = persist_markdown_atomic(markdown, output_dir, paper.title)
    return ReviewRunResult(status=ReviewRunStatus.SAVED, output_path=output_path, metadata=metadata)


def _input_refusal(pdf_path: Path) -> Refusal | None:
    if not pdf_path.exists():
        return Refusal(
            reason="PDF input was refused before extraction",
            diagnostics=[GateResult(status=GateStatus.REJECT, reasons=[f"input_not_found: {pdf_path}"])],
        )
    if not pdf_path.is_file():
        return Refusal(
            reason="PDF input was refused before extraction",
            diagnostics=[GateResult(status=GateStatus.REJECT, reasons=[f"input_not_file: {pdf_path}"])],
        )
    if pdf_path.suffix.lower() != ".pdf":
        return Refusal(
            reason="PDF input was refused before extraction",
            diagnostics=[GateResult(status=GateStatus.REJECT, reasons=["input_not_pdf: input must be a PDF file"])],
        )
    size_bytes = pdf_path.stat().st_size
    if size_bytes > MAX_PDF_BYTES:
        return Refusal(
            reason="PDF input was refused before extraction",
            diagnostics=[
                GateResult(
                    status=GateStatus.REJECT,
                    reasons=[f"input_too_large: PDF is {size_bytes} bytes; maximum is {MAX_PDF_BYTES} bytes"],
                )
            ],
        )
    return None


def _pdf_extractor(config: ReviewConfig) -> PdfExtractor:
    if not config.ocr_enabled:
        return PdfExtractor(ocr_adapter=NullOcrAdapter())
    try:
        ocr_adapter = TesseractOcrAdapter(tesseract_cmd=config.tesseract_cmd)
    except RuntimeError as exc:
        raise ReviewOrchestrationError(f"OCR is enabled but Tesseract OCR is not available: {exc}") from exc
    return PdfExtractor(ocr_adapter=ocr_adapter)


def _llm_client(config: ReviewConfig) -> LlmClient:
    if config.llm.provider is LlmProvider.FAKE:
        return FakeLlmClient()
    raise ReviewOrchestrationError("hosted LLM clients are not wired in this checkpoint")
