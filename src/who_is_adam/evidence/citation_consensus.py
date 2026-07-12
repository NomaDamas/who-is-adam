"""Cross-provider agreement checks for normalized citation metadata."""

from __future__ import annotations

import re
from collections.abc import Mapping

from who_is_adam.evidence.citation_matching import (
    AUTHOR_OVERLAP_THRESHOLD,
    TITLE_MATCH_THRESHOLD,
    VENUE_MATCH_THRESHOLD,
    title_similarity,
    venue_similarity,
)
from who_is_adam.evidence.citation_metadata import normalize_identifier, normalize_text


def provider_metadata_agree(
    left: Mapping[str, str | int | float | bool | None],
    right: Mapping[str, str | int | float | bool | None],
) -> bool:
    """Confirm two provider records describe the same paper."""
    left_title = left.get("matched_title")
    right_title = right.get("matched_title")
    if isinstance(left_title, str) and isinstance(right_title, str):
        if title_similarity(left_title, right_title) < TITLE_MATCH_THRESHOLD:
            return False
    left_authors = left.get("matched_authors")
    right_authors = right.get("matched_authors")
    if isinstance(left_authors, str) and isinstance(right_authors, str):
        if (
            _author_overlap(left_authors.split(";"), right_authors.split(";"))
            < AUTHOR_OVERLAP_THRESHOLD
        ):
            return False
    for key in ("matched_year", "matched_volume", "matched_issue"):
        left_value = left.get(key)
        right_value = right.get(key)
        if left_value is not None and right_value is not None:
            if normalize_text(str(left_value)) != normalize_text(str(right_value)):
                return False
    for key in ("matched_doi", "matched_arxiv_id"):
        left_value = left.get(key)
        right_value = right.get(key)
        if isinstance(left_value, str) and isinstance(right_value, str):
            if normalize_identifier(left_value) != normalize_identifier(right_value):
                return False
    left_pages = left.get("matched_pages")
    right_pages = right.get("matched_pages")
    if isinstance(left_pages, str) and isinstance(right_pages, str):
        if _normalize_pages(left_pages) != _normalize_pages(right_pages):
            return False
    for key in ("matched_venue", "matched_publisher"):
        left_value = left.get(key)
        right_value = right.get(key)
        if isinstance(left_value, str) and isinstance(right_value, str):
            score = (
                venue_similarity(left_value, right_value)
                if key == "matched_venue"
                else title_similarity(left_value, right_value)
            )
            if score < VENUE_MATCH_THRESHOLD:
                return False
    return True


def _author_overlap(left: list[str], right: list[str]) -> float:
    left_names = {_surname(name) for name in left if _surname(name)}
    right_names = {_surname(name) for name in right if _surname(name)}
    if not left_names or not right_names:
        return 0.0
    return len(left_names & right_names) / max(len(left_names), len(right_names)) * 100


def _surname(name: str) -> str:
    if "," in name:
        return normalize_text(name.split(",", 1)[0])
    normalized = normalize_text(name)
    return normalized.split()[-1] if normalized else ""


def _normalize_pages(value: str) -> str:
    return re.sub(r"\s*[-–—]+\s*", "-", value.strip())
