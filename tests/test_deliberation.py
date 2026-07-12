from __future__ import annotations

from typer.testing import CliRunner

from who_is_adam.cli import app
from who_is_adam.llm.base import FakeLlmClient
from who_is_adam.models import EvidenceSpan, Finding, ReviewScores, SpecialistReview
from who_is_adam.review.deliberation import run_review_deliberation
from who_is_adam.review.prompts import deliberation_prompt, synthesis_prompt


runner = CliRunner()


def _specialist(role: str) -> SpecialistReview:
    evidence = EvidenceSpan(page=1, section="Abstract", text="The paper states its claim.")
    return SpecialistReview(
        role=role,
        findings=[Finding(claim=f"{role} finding", evidence=[evidence])],
        scores=ReviewScores(
            soundness=3,
            presentation=3,
            significance=3,
            originality=3,
            overall_recommendation=4,
            confidence=3,
        ),
        evidence=[evidence],
    )


def test_deliberation_adds_devil_advocate_debate_and_meta_review() -> None:
    reviews = [
        _specialist("methodology"),
        _specialist("empirical-evidence"),
        _specialist("novelty-significance"),
        _specialist("presentation-clarity"),
        _specialist("ethics-reproducibility"),
    ]

    report = run_review_deliberation(
        specialist_reviews=reviews,
        llm_client=FakeLlmClient(),
    )

    assert report.devil_advocate.critical_objections
    assert report.debate_rounds
    assert report.meta_review.consistency_checks
    assert report.meta_review.validity_checks
    assert report.dialectical_synthesis
    assert report.required_synthesis_constraints


def test_cli_output_records_deliberation_appendix(tmp_path, pdf_fixtures) -> None:
    result = runner.invoke(
        app,
        [
            "review",
            str(pdf_fixtures / "valid_icml_text.pdf"),
            "--output-dir",
            str(tmp_path),
            "--llm-policy",
            "ICML 2026 Main Track LLM policy",
            "--code-of-conduct-ack",
            "--offline",
        ],
    )

    assert result.exit_code == 0, result.stderr
    output_path = (
        tmp_path
        / "deterministic-icml-fixture-for-safety-gates"
        / "deterministic-icml-fixture-for-safety-gates_review_1.md"
    )
    markdown = output_path.read_text(encoding="utf-8")

    assert '"review_deliberation"' in markdown
    assert '"devil_advocate"' in markdown
    assert '"meta_review"' in markdown
    assert "Deterministic offline summary." in markdown


def test_deliberation_prompt_has_total_byte_limit() -> None:
    prompt = deliberation_prompt(specialist_reviews_json='{"finding":"' + "x" * 2_000_000 + '"}')

    assert len(prompt.encode("utf-8")) <= 96_000
    assert "[truncated to prompt budget]" in prompt
    assert prompt.count("</untrusted_specialist_reviews>") == 1


def test_synthesis_prompt_has_total_byte_limit() -> None:
    prompt = synthesis_prompt(
        specialist_reviews_json='{"finding":"' + "x" * 2_000_000 + '"}',
        deliberation_json='{"debate":"' + "y" * 2_000_000 + '"}',
    )

    assert len(prompt.encode("utf-8")) <= 96_000
    assert prompt.count("[truncated to prompt budget]") == 2
    assert prompt.count("</untrusted_specialist_reviews>") == 1
    assert prompt.count("</untrusted_review_deliberation>") == 1
