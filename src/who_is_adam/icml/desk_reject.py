"""Evidence-bearing ICML Main Track desk-reject checks."""

from __future__ import annotations

import re
from collections.abc import Iterable

from who_is_adam.icml.constants import DESK_REJECT_RULE_ORDER, RULE_LABELS
from who_is_adam.models import CheckStatus, DeskRejectCheck, EvidenceSpan, PaperStructure

_AUTHOR_HINTS = re.compile(r"\b(author|affiliation|university|institute|corresponding|acknowledg(e)?ments?)\b", re.IGNORECASE)
_CHECKLIST_HINT = re.compile(r"\b(checklist|submission checklist|reproducibility checklist)\b", re.IGNORECASE)
_ETHICS_HINT = re.compile(r"\b(ethic|broader impact|societal impact|human subjects|irb)\b", re.IGNORECASE)
_REPRO_HINT = re.compile(r"\b(code|data|dataset|reproducib|hyperparameter|random seed|artifact)\b", re.IGNORECASE)
_LLM_HINT = re.compile(r"\b(generative ai|large language model|\bllm\b|chatgpt|gpt-4|claude)\b", re.IGNORECASE)
_SCOPE_HINT = re.compile(r"\b(machine learning|learning algorithm|neural|model|optimization|dataset|benchmark)\b", re.IGNORECASE)
_DUAL_HINT = re.compile(r"\b(under review|submitted to|dual submission|concurrent submission)\b", re.IGNORECASE)
_SUPP_HINT = re.compile(r"\b(supplementary|appendix|supplemental)\b", re.IGNORECASE)
_TEMPLATE_HINT = re.compile(r"\bICML\b|International Conference on Machine Learning", re.IGNORECASE)


def run_desk_reject_checks(structure: PaperStructure, *, supplementary_provided: bool = False) -> tuple[DeskRejectCheck, ...]:
    """Run deterministic desk checks without fabricating official-rule certainty.

    Hard, directly observable violations fail. Heuristic or absent signals are UNKNOWN rather than FAIL.
    """

    checks = {
        "ICML-MAIN-FORMAT-PAGE-LIMIT": _page_limit(structure),
        "ICML-MAIN-FORMAT-TEMPLATE": _heuristic_check(structure, "ICML-MAIN-FORMAT-TEMPLATE", _TEMPLATE_HINT, "template conformance cannot be proven from extracted text"),
        "ICML-MAIN-ANONYMITY": _anonymity(structure),
        "ICML-MAIN-SUPPLEMENTARY": _supplementary(structure, supplementary_provided=supplementary_provided),
        "ICML-MAIN-CHECKLIST": _heuristic_check(structure, "ICML-MAIN-CHECKLIST", _CHECKLIST_HINT, "checklist not detected in extracted text"),
        "ICML-MAIN-ETHICS": _heuristic_check(structure, "ICML-MAIN-ETHICS", _ETHICS_HINT, "ethics disclosure not detected in extracted text"),
        "ICML-MAIN-REPRODUCIBILITY": _heuristic_check(structure, "ICML-MAIN-REPRODUCIBILITY", _REPRO_HINT, "reproducibility evidence not detected in extracted text"),
        "ICML-MAIN-LLM-DISCLOSURE": _heuristic_check(structure, "ICML-MAIN-LLM-DISCLOSURE", _LLM_HINT, "LLM-use disclosure not detected; absence may be compliant if no LLMs were used"),
        "ICML-MAIN-SCOPE": _heuristic_check(structure, "ICML-MAIN-SCOPE", _SCOPE_HINT, "ICML scope fit is ambiguous from deterministic text heuristics"),
        "ICML-MAIN-DUAL-SUBMISSION": _dual_submission(structure),
    }
    return tuple(checks[rule_id] for rule_id in DESK_REJECT_RULE_ORDER)


def blocking_checks(checks: Iterable[DeskRejectCheck]) -> tuple[DeskRejectCheck, ...]:
    return tuple(check for check in checks if check.status is CheckStatus.FAIL)


def _check(rule_id: str, status: CheckStatus, *, evidence: list[EvidenceSpan] | None = None, diagnostic: str | None = None) -> DeskRejectCheck:
    return DeskRejectCheck(
        rule_id=rule_id,
        label=RULE_LABELS[rule_id],
        status=status,
        evidence=evidence or [],
        diagnostic=diagnostic,
    )


def _page_limit(structure: PaperStructure) -> DeskRejectCheck:
    page_count = structure.extraction_metrics.page_count
    span = EvidenceSpan(page=1, section="PDF metadata", text=f"Extracted page count: {page_count}")
    if page_count > 8:
        return _check("ICML-MAIN-FORMAT-PAGE-LIMIT", CheckStatus.FAIL, evidence=[span], diagnostic="main PDF exceeds the ICML Main Track 8-page content limit heuristic")
    return _check("ICML-MAIN-FORMAT-PAGE-LIMIT", CheckStatus.PASS, evidence=[span])


def _anonymity(structure: PaperStructure) -> DeskRejectCheck:
    front_matter = "\n".join(structure.pages[:2])
    matches = _matches(front_matter, _AUTHOR_HINTS, limit=3)
    if matches:
        return _check("ICML-MAIN-ANONYMITY", CheckStatus.UNKNOWN, evidence=[EvidenceSpan(page=1, section="Front matter", text=text) for text in matches], diagnostic="possible author/affiliation text detected; deterministic heuristic cannot prove anonymity violation")
    return _check("ICML-MAIN-ANONYMITY", CheckStatus.PASS)


def _supplementary(structure: PaperStructure, *, supplementary_provided: bool) -> DeskRejectCheck:
    if supplementary_provided:
        return _check("ICML-MAIN-SUPPLEMENTARY", CheckStatus.PASS, diagnostic="supplementary PDF was supplied separately")
    matches = _matches("\n".join(structure.pages), _SUPP_HINT, limit=3)
    if matches:
        return _check("ICML-MAIN-SUPPLEMENTARY", CheckStatus.UNKNOWN, evidence=[EvidenceSpan(page=1, section="Document text", text=text) for text in matches], diagnostic="paper mentions supplementary material but no supplementary PDF was supplied")
    return _check("ICML-MAIN-SUPPLEMENTARY", CheckStatus.PASS)


def _dual_submission(structure: PaperStructure) -> DeskRejectCheck:
    matches = _matches("\n".join(structure.pages), _DUAL_HINT, limit=3)
    if matches:
        return _check("ICML-MAIN-DUAL-SUBMISSION", CheckStatus.UNKNOWN, evidence=[EvidenceSpan(page=1, section="Document text", text=text) for text in matches], diagnostic="possible concurrent-submission language detected; public text heuristic is ambiguous")
    return _check("ICML-MAIN-DUAL-SUBMISSION", CheckStatus.PASS)


def _heuristic_check(structure: PaperStructure, rule_id: str, pattern: re.Pattern[str], unknown_diagnostic: str) -> DeskRejectCheck:
    matches = _matches("\n".join(structure.pages), pattern, limit=3)
    if matches:
        return _check(rule_id, CheckStatus.PASS, evidence=[EvidenceSpan(page=1, section="Document text", text=text) for text in matches])
    return _check(rule_id, CheckStatus.UNKNOWN, diagnostic=unknown_diagnostic)


def _matches(text: str, pattern: re.Pattern[str], *, limit: int) -> list[str]:
    excerpts: list[str] = []
    for match in pattern.finditer(text):
        left = max(0, match.start() - 80)
        right = min(len(text), match.end() + 80)
        excerpt = re.sub(r"\s+", " ", text[left:right]).strip()[:500]
        if excerpt and excerpt not in excerpts:
            excerpts.append(excerpt)
        if len(excerpts) >= limit:
            break
    return excerpts
