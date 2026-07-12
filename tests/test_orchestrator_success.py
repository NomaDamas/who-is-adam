from __future__ import annotations

from typer.testing import CliRunner

from who_is_adam.cli import app

from who_is_adam.llm.base import FakeLlmClient
from who_is_adam.models import RuntimeMetadata, SpecialistReview, SynthesizedReview
from who_is_adam.output.markdown import OFFICIAL_SECTION_ORDER, SCORE_SCALE_TEXT, render_review_markdown
from who_is_adam.output.paths import persist_markdown_atomic


runner = CliRunner()


def _official_headings(markdown: str) -> list[str]:
    return [line.removeprefix("## ") for line in markdown.splitlines() if line.startswith("## ")]


def test_fake_review_renders_exact_official_headings_and_scales(tmp_path) -> None:
    payload = FakeLlmClient().complete_json("role: synthesis", SynthesizedReview)
    review = SynthesizedReview.model_validate(payload)
    metadata = RuntimeMetadata(
        llm_policy_checked=True,
        llm_policy_name="ICML 2026 Main Track LLM policy",
        code_of_conduct_acknowledged=True,
        official_docs_checked_at="2026-07-12",
        provider_mode="fake",
        fixed_run_timestamp="2026-07-12T00:00:00Z",
    )

    markdown = render_review_markdown(review, metadata=metadata)
    output_path = persist_markdown_atomic(markdown, tmp_path, "Deterministic Offline Paper")

    assert output_path == tmp_path / "deterministic-offline-paper" / "deterministic-offline-paper_review_1.md"
    assert output_path.read_text(encoding="utf-8") == markdown
    assert _official_headings(markdown) == [*OFFICIAL_SECTION_ORDER, "Appendix: Metadata"]
    for title, scale in SCORE_SCALE_TEXT.items():
        assert f"## {title}\n\n" in markdown
        assert f"Scale: {scale}" in markdown
    assert "Deterministic offline summary." in markdown
    assert "ICML 2026 Main Track LLM policy" in markdown


def test_fake_llm_returns_schema_appropriate_specialist_review() -> None:
    payload = FakeLlmClient().complete_json("role: methodology", SpecialistReview)
    review = SpecialistReview.model_validate(payload)

    assert review.role == "methodology"
    assert review.findings[0].claim == "Deterministic specialist finding cites extracted paper evidence."
    assert review.findings[0].evidence[0].text == "Deterministic offline evidence."
    assert review.scores.soundness == 3
    assert review.scores.overall_recommendation == 4


def test_review_remains_documented_subcommand() -> None:
    help_result = runner.invoke(app, ["review", "--help"])

    assert help_result.exit_code == 0
    assert "PDF_PATH" in help_result.stdout

    smoke_result = runner.invoke(app, ["review", "paper.pdf"])

    assert smoke_result.exit_code == 3
    assert "--llm-policy is required" in smoke_result.stderr


def test_offline_cli_runs_specialists_and_saves_review(tmp_path, pdf_fixtures) -> None:
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
    assert "Review saved:" in result.stdout
    output_path = (
        tmp_path
        / "deterministic-icml-fixture-for-safety-gates"
        / "deterministic-icml-fixture-for-safety-gates_review_1.md"
    )
    markdown = output_path.read_text(encoding="utf-8")
    assert "Deterministic offline summary." in markdown
    assert "ICML 2026 Main Track LLM policy" in markdown


def test_offline_cli_refuses_prompt_injection_without_internal_error(tmp_path, pdf_fixtures) -> None:
    result = runner.invoke(
        app,
        [
            "review",
            str(pdf_fixtures / "prompt_injection.pdf"),
            "--output-dir",
            str(tmp_path),
            "--llm-policy",
            "ICML 2026 Main Track LLM policy",
            "--code-of-conduct-ack",
            "--offline",
        ],
    )

    assert result.exit_code == 2
    assert "Review refused:" in result.stderr
    assert "Internal error: 2" not in result.stderr
    assert result.stderr.count("Internal error:") == 0
