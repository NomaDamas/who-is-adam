"""Official ICML Main Track review constants and rule identifiers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreScale:
    """Inclusive integer scale used by the ICML review form."""

    name: str
    minimum: int
    maximum: int
    labels: tuple[str, ...]

    def validate(self, value: int) -> int:
        if not self.minimum <= value <= self.maximum:
            raise ValueError(f"{self.name} must be between {self.minimum} and {self.maximum}")
        return value


OFFICIAL_TRACK = "main"
VENUE = "icml"

SECTION_ORDER: tuple[str, ...] = (
    "Summary",
    "Strengths And Weaknesses",
    "Questions",
    "Limitations",
    "Soundness",
    "Presentation",
    "Contribution",
    "Rating",
    "Confidence",
    "Ethical Concerns",
    "Reproducibility Notes",
    "Evidence",
    "Consensus",
    "Conflicts",
    "Minority Opinions",
)

SOUNDNESS_SCALE = ScoreScale("Soundness", 1, 4, ("poor", "fair", "good", "excellent"))
PRESENTATION_SCALE = ScoreScale("Presentation", 1, 4, ("poor", "fair", "good", "excellent"))
CONTRIBUTION_SCALE = ScoreScale("Contribution", 1, 4, ("poor", "fair", "good", "excellent"))
RATING_SCALE = ScoreScale(
    "Rating",
    1,
    6,
    ("strong reject", "reject", "weak reject", "weak accept", "accept", "strong accept"),
)
CONFIDENCE_SCALE = ScoreScale(
    "Confidence",
    1,
    5,
    ("low", "somewhat low", "medium", "high", "very high"),
)

SCORE_SCALES: dict[str, ScoreScale] = {
    "soundness": SOUNDNESS_SCALE,
    "presentation": PRESENTATION_SCALE,
    "significance": CONTRIBUTION_SCALE,
    "overall_recommendation": RATING_SCALE,
    "confidence": CONFIDENCE_SCALE,
}

RULE_PAGE_LIMIT = "ICML-MAIN-FORMAT-PAGE-LIMIT"
RULE_TEMPLATE = "ICML-MAIN-FORMAT-TEMPLATE"
RULE_ANONYMITY = "ICML-MAIN-ANONYMITY"
RULE_SUPPLEMENTARY = "ICML-MAIN-SUPPLEMENTARY"
RULE_CHECKLIST = "ICML-MAIN-CHECKLIST"
RULE_ETHICS = "ICML-MAIN-ETHICS"
RULE_REPRODUCIBILITY = "ICML-MAIN-REPRODUCIBILITY"
RULE_LLM_DISCLOSURE = "ICML-MAIN-LLM-DISCLOSURE"
RULE_SCOPE = "ICML-MAIN-SCOPE"
RULE_DUAL_SUBMISSION = "ICML-MAIN-DUAL-SUBMISSION"

DESK_REJECT_RULE_ORDER: tuple[str, ...] = (
    RULE_PAGE_LIMIT,
    RULE_TEMPLATE,
    RULE_ANONYMITY,
    RULE_SUPPLEMENTARY,
    RULE_CHECKLIST,
    RULE_ETHICS,
    RULE_REPRODUCIBILITY,
    RULE_LLM_DISCLOSURE,
    RULE_SCOPE,
    RULE_DUAL_SUBMISSION,
)

RULE_LABELS: dict[str, str] = {
    RULE_PAGE_LIMIT: "Main Track page limit",
    RULE_TEMPLATE: "Official ICML template and formatting",
    RULE_ANONYMITY: "Double-blind anonymity",
    RULE_SUPPLEMENTARY: "Supplementary material separation",
    RULE_CHECKLIST: "Required checklist",
    RULE_ETHICS: "Ethics and broader impacts disclosure",
    RULE_REPRODUCIBILITY: "Reproducibility information",
    RULE_LLM_DISCLOSURE: "Generative AI / LLM assistance disclosure",
    RULE_SCOPE: "ICML Main Track scope",
    RULE_DUAL_SUBMISSION: "Dual submission policy",
}

PUBLIC_EVIDENCE_ONLY = "public_evidence_only"
MAX_DIRECT_COMPARISON_CLAIMS = 5
