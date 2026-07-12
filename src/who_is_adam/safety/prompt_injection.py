"""Deterministic prompt-injection detection for untrusted PDF text."""

from __future__ import annotations

import re
from dataclasses import dataclass

from who_is_adam.models import EvidenceSpan, GateResult, GateStatus, PaperStructure

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ignore_instructions", re.compile(r"\b(ignore|disregard|forget)\b.{0,80}\b(previous|prior|system|developer|reviewer)\b.{0,80}\b(instruction|prompt|policy|guideline)s?\b", re.IGNORECASE | re.DOTALL)),
    ("system_override", re.compile(r"\b(system|developer)\s+(prompt|message|instruction)s?\b|\bnew\s+instructions?\s+for\s+(the\s+)?(reviewer|llm|model)\b", re.IGNORECASE)),
    ("score_manipulation", re.compile(r"\b(give|assign|output|return)\b.{0,80}\b(accept|strong accept|score\s*[45]|high score|positive review)\b", re.IGNORECASE | re.DOTALL)),
    ("tool_policy_override", re.compile(r"\b(change|override|disable|bypass)\b.{0,80}\b(policy|safety|tool|json schema|quality gate|gate)\b", re.IGNORECASE | re.DOTALL)),
    ("secret_exfiltration", re.compile(r"\b(reveal|print|dump|exfiltrate)\b.{0,80}\b(api key|secret|system prompt|hidden instruction|environment)\b", re.IGNORECASE | re.DOTALL)),
    ("hidden_text_marker", re.compile(r"\b(white text|hidden text|invisible instruction|prompt injection)\b", re.IGNORECASE)),
)


@dataclass(frozen=True)
class InjectionFinding:
    """One deterministic prompt-injection hit."""

    rule_id: str
    page: int
    excerpt: str


def detect_prompt_injection(structure: PaperStructure) -> GateResult:
    """Reject when PDF text contains instructions aimed at reviewers or models."""

    findings = list(iter_findings(structure.pages))
    if not findings:
        return GateResult(status=GateStatus.PASS)
    return GateResult(
        status=GateStatus.REJECT,
        reasons=[f"prompt injection pattern detected: {finding.rule_id}" for finding in findings],
        evidence=[EvidenceSpan(page=finding.page, section="Safety", text=finding.excerpt) for finding in findings],
    )


def iter_findings(pages: list[str]) -> list[InjectionFinding]:
    findings: list[InjectionFinding] = []
    seen: set[tuple[str, int, str]] = set()
    for page_number, page in enumerate(pages, start=1):
        normalized = _normalize(page)
        for rule_id, pattern in _PATTERNS:
            for match in pattern.finditer(normalized):
                excerpt = _excerpt(normalized, match.start(), match.end())
                key = (rule_id, page_number, excerpt)
                if key not in seen:
                    findings.append(InjectionFinding(rule_id=rule_id, page=page_number, excerpt=excerpt))
                    seen.add(key)
    return findings


def _normalize(text: str) -> str:
    return re.sub(r"[\u200b-\u200f\ufeff]", "", text)


def _excerpt(text: str, start: int, end: int, *, context: int = 80) -> str:
    left = max(0, start - context)
    right = min(len(text), end + context)
    return re.sub(r"\s+", " ", text[left:right]).strip()[:500]
