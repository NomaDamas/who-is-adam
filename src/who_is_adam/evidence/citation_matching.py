"""Multi-field citation candidate normalization and matching."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from rapidfuzz import fuzz

from who_is_adam.models import ProviderStatus, ReferenceEntry

from .citation_metadata import (
    normalize_candidate,
    normalize_identifier,
    normalize_text,
)

TITLE_MATCH_THRESHOLD: Final = 85.0
MIN_TITLE_SIMILARITY: Final = 70.0
AUTHOR_OVERLAP_THRESHOLD: Final = 30.0
VENUE_MATCH_THRESHOLD: Final = 70.0

_VENUE_ALIASES: Final[dict[str, str]] = {
    "international conference on machine learning": "icml",
    "advances in neural information processing systems": "neurips",
    "neural information processing systems": "neurips",
    "international conference on learning representations": "iclr",
    "association for computational linguistics": "acl",
    "conference on empirical methods in natural language processing": "emnlp",
    "computer vision and pattern recognition": "cvpr",
    "journal of machine learning research": "jmlr",
}


@dataclass(frozen=True, slots=True)
class MatchResult:
    status: ProviderStatus
    diagnostic: str | None
    metadata: dict[str, str | int | float | bool | None]


def select_best_candidate(
    reference: ReferenceEntry, candidates: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    """Return the highest-title-similarity candidate above the fallback threshold."""
    if not reference.title:
        return candidates[0] if candidates else None
    best: Mapping[str, Any] | None = None
    best_score = 0.0
    for candidate in candidates[:5]:
        title = normalize_candidate(candidate).title
        score = title_similarity(reference.title, title)
        if score > best_score:
            best = candidate
            best_score = score
    return best if best is not None and best_score >= MIN_TITLE_SIMILARITY else None


def match_reference(reference: ReferenceEntry, candidate: Mapping[str, Any]) -> MatchResult:
    """Compare title, year, author surnames, venue, DOI, and arXiv identifier."""
    normalized = normalize_candidate(candidate)
    if not normalized.title:
        return MatchResult(
            ProviderStatus.METADATA_ERROR,
            "candidate is missing a title",
            {},
        )
    if not reference.title:
        return MatchResult(
            ProviderStatus.NEEDS_REVIEW,
            "reference title could not be parsed",
            {"matched_title": normalized.title},
        )

    title_score = title_similarity(reference.title, normalized.title)
    year_match = _exact_optional(reference.year, normalized.year)
    author_overlap = _author_overlap(reference.authors, normalized.authors)
    author_match = (
        None
        if not reference.authors or not normalized.authors
        else _authors_match(reference.authors, normalized.authors, author_overlap)
    )
    venue_score = _optional_similarity(reference.venue, normalized.venue, venue=True)
    venue_match = None if venue_score is None else venue_score >= VENUE_MATCH_THRESHOLD
    volume_match = _text_match(reference.volume, normalized.volume)
    issue_match = _text_match(reference.issue, normalized.issue)
    pages_match = _pages_match(reference.pages, normalized.pages)
    publisher_score = _optional_similarity(reference.publisher, normalized.publisher)
    publisher_match = None if publisher_score is None else publisher_score >= VENUE_MATCH_THRESHOLD
    doi_match = _identifier_match(reference.doi, normalized.doi)
    arxiv_match = _identifier_match(reference.arxiv_id, normalized.arxiv_id)
    identifier_match = doi_match is True or arxiv_match is True

    metadata: dict[str, str | int | float | bool | None] = {
        "matched_title": normalized.title,
        "matched_authors": "; ".join(normalized.authors) or None,
        "matched_year": normalized.year,
        "matched_venue": normalized.venue,
        "matched_volume": normalized.volume,
        "matched_issue": normalized.issue,
        "matched_pages": normalized.pages,
        "matched_publisher": normalized.publisher,
        "matched_doi": normalized.doi,
        "matched_arxiv_id": normalized.arxiv_id,
        "title_score": round(title_score, 1),
        "year_match": year_match,
        "author_overlap": round(author_overlap, 1) if author_match is not None else None,
        "author_match": author_match,
        "venue_score": round(venue_score, 1) if venue_score is not None else None,
        "venue_match": venue_match,
        "volume_match": volume_match,
        "issue_match": issue_match,
        "pages_match": pages_match,
        "publisher_score": round(publisher_score, 1) if publisher_score is not None else None,
        "publisher_match": publisher_match,
        "doi_match": doi_match,
        "arxiv_id_match": arxiv_match,
        "identifier_match": identifier_match,
    }

    if title_score < MIN_TITLE_SIMILARITY:
        status = ProviderStatus.NEEDS_REVIEW if identifier_match else ProviderStatus.NOT_FOUND
        diagnostic = (
            "identifier resolved to conflicting title"
            if identifier_match
            else "candidate title did not match reference"
        )
        return MatchResult(status, diagnostic, metadata)
    if title_score < TITLE_MATCH_THRESHOLD:
        return MatchResult(
            ProviderStatus.NEEDS_REVIEW,
            "closest candidate title requires human review",
            metadata,
        )

    conflicts = [
        field
        for field, matched in (
            ("year", year_match),
            ("authors", author_match),
            ("venue", venue_match),
            ("volume", volume_match),
            ("issue", issue_match),
            ("pages", pages_match),
            ("publisher", publisher_match),
            ("doi", doi_match),
            ("arxiv_id", arxiv_match),
        )
        if matched is False
    ]
    if conflicts:
        metadata["mismatch_fields"] = ",".join(conflicts)
        return MatchResult(
            ProviderStatus.NEEDS_REVIEW,
            f"conflicting citation fields: {', '.join(conflicts)}",
            metadata,
        )

    corroborating_matches = sum(
        matched is True
        for matched in (
            year_match,
            author_match,
            venue_match,
            volume_match,
            issue_match,
            pages_match,
            publisher_match,
            doi_match,
            arxiv_match,
        )
    )
    if corroborating_matches == 0:
        return MatchResult(
            ProviderStatus.WEAK_MATCH,
            "title matched but no independent metadata field was available",
            metadata,
        )
    return MatchResult(ProviderStatus.VERIFIED, None, metadata)


def title_similarity(left: str, right: str) -> float:
    return float(fuzz.token_sort_ratio(normalize_text(left), normalize_text(right)))


def _author_overlap(left: Sequence[str], right: Sequence[str]) -> float:
    left_names = {_surname(name) for name in left if _surname(name)}
    right_names = {_surname(name) for name in right if _surname(name)}
    if not left_names or not right_names:
        return 0.0
    return len(left_names & right_names) / max(len(left_names), len(right_names)) * 100


def _authors_match(left: Sequence[str], right: Sequence[str], overlap: float) -> bool:
    abbreviated = [name for name in left if "et al" in normalize_text(name)]
    if abbreviated:
        lead_surname = _surname(abbreviated[0])
        return lead_surname in {_surname(name) for name in right}
    return overlap >= AUTHOR_OVERLAP_THRESHOLD


def _surname(name: str) -> str:
    if "," in name:
        return normalize_text(name.split(",", 1)[0])
    normalized = normalize_text(name)
    if not normalized:
        return ""
    if " et al" in normalized:
        return normalized.split()[0]
    return normalized.split()[-1]


def _exact_optional(left: int | None, right: int | None) -> bool | None:
    return None if left is None or right is None else left == right


def _identifier_match(left: str | None, right: str | None) -> bool | None:
    if not left or not right:
        return None
    return normalize_identifier(left) == normalize_identifier(right)


def _text_match(left: str | None, right: str | None) -> bool | None:
    if not left or not right:
        return None
    return normalize_text(left) == normalize_text(right)


def _pages_match(left: str | None, right: str | None) -> bool | None:
    if not left or not right:
        return None
    left_pages = re.sub(r"\s*[-–—]+\s*", "-", left.strip())
    right_pages = re.sub(r"\s*[-–—]+\s*", "-", right.strip())
    return left_pages == right_pages


def _optional_similarity(
    left: str | None, right: str | None, *, venue: bool = False
) -> float | None:
    if not left or not right:
        return None
    left_value = _normalize_venue(left) if venue else normalize_text(left)
    right_value = _normalize_venue(right) if venue else normalize_text(right)
    return float(fuzz.token_sort_ratio(left_value, right_value))


def _normalize_venue(value: str) -> str:
    normalized = re.sub(r"\b(?:18|19|20)\d{2}\b", "", normalize_text(value)).strip()
    for full, abbreviation in _VENUE_ALIASES.items():
        if full in normalized:
            return abbreviation
    return normalized


def venue_similarity(left: str, right: str) -> float:
    return float(fuzz.token_sort_ratio(_normalize_venue(left), _normalize_venue(right)))
