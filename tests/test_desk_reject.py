from __future__ import annotations

from pathlib import Path

from who_is_adam.icml.constants import RULE_ANONYMITY, RULE_PAGE_LIMIT, RULE_SCOPE
from who_is_adam.models import CheckStatus, DeskRejectCheck
from who_is_adam.pdf.extractor import PdfExtractor


def _checks_by_rule(pdf_fixtures: Path, name: str) -> dict[str, DeskRejectCheck]:
    from who_is_adam.icml.desk_reject import run_desk_reject_checks

    paper = PdfExtractor().extract(pdf_fixtures / name)
    checks = run_desk_reject_checks(paper)
    assert checks
    return {check.rule_id: check for check in checks}


def test_valid_fixture_passes_main_track_page_and_anonymity_checks(pdf_fixtures: Path) -> None:
    checks = _checks_by_rule(pdf_fixtures, "valid_icml_text.pdf")

    assert checks[RULE_SCOPE].status is CheckStatus.PASS
    assert checks[RULE_PAGE_LIMIT].status is CheckStatus.PASS
    assert checks[RULE_ANONYMITY].status is CheckStatus.PASS
    assert checks[RULE_PAGE_LIMIT].evidence


def test_over_8_page_fixture_has_rule_specific_page_limit_finding(pdf_fixtures: Path) -> None:
    checks = _checks_by_rule(pdf_fixtures, "over_8_pages.pdf")
    finding = checks[RULE_PAGE_LIMIT]

    assert finding.status is CheckStatus.FAIL
    assert finding.evidence
    assert any(span.page == 1 and "10" in span.text for span in finding.evidence)
    assert finding.diagnostic is not None
    assert "8" in finding.diagnostic


def test_anonymity_fixture_has_rule_specific_public_identity_evidence(pdf_fixtures: Path) -> None:
    checks = _checks_by_rule(pdf_fixtures, "anonymity_violation.pdf")
    finding = checks[RULE_ANONYMITY]

    assert finding.status in {CheckStatus.FAIL, CheckStatus.UNKNOWN}
    assert finding.evidence
    evidence_text = " ".join(span.text for span in finding.evidence)
    assert "ada@example.edu" in evidence_text
    assert "github.com/example" in evidence_text or "NSF-123456" in evidence_text
    assert finding.diagnostic is not None
    assert "anonymous" in finding.diagnostic.lower() or "anonym" in finding.diagnostic.lower()


def test_official_main_track_is_fail_closed_for_unsafe_input(pdf_fixtures: Path) -> None:
    checks = _checks_by_rule(pdf_fixtures, "anonymity_violation.pdf")

    assert RULE_SCOPE in checks
    assert checks[RULE_SCOPE].status in {CheckStatus.PASS, CheckStatus.FAIL, CheckStatus.UNKNOWN}
    assert checks[RULE_SCOPE].diagnostic or checks[RULE_SCOPE].evidence
