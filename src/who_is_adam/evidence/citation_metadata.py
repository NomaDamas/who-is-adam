"""Normalize provider-specific citation metadata into one record."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from who_is_adam.models import ReferenceEntry


@dataclass(frozen=True, slots=True)
class NormalizedCandidate:
    title: str
    authors: tuple[str, ...]
    year: int | None
    venue: str | None
    volume: str | None
    issue: str | None
    pages: str | None
    publisher: str | None
    doi: str | None
    arxiv_id: str | None


def normalize_candidate(candidate: Mapping[str, Any]) -> NormalizedCandidate:
    """Convert supported provider response shapes into one comparison record."""
    return NormalizedCandidate(
        title=_candidate_title(candidate),
        authors=tuple(_candidate_authors(candidate)),
        year=_candidate_year(candidate),
        venue=_candidate_venue(candidate),
        volume=_candidate_string(candidate, "volume"),
        issue=_candidate_string(candidate, "issue", "number"),
        pages=_candidate_pages(candidate),
        publisher=_candidate_publisher(candidate),
        doi=_candidate_doi(candidate),
        arxiv_id=_candidate_arxiv_id(candidate),
    )


def normalized_reference_key(reference: ReferenceEntry) -> str | None:
    """Return a stable key for exact duplicate citation detection."""
    if reference.doi:
        return f"doi:{normalize_identifier(reference.doi)}"
    if reference.arxiv_id:
        return f"arxiv:{normalize_identifier(reference.arxiv_id)}"
    if reference.title:
        return f"title:{normalize_text(reference.title)}:{reference.year or ''}"
    return None


def normalize_identifier(value: str) -> str:
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value.strip().casefold()).rstrip(".,")


def normalize_text(value: str) -> str:
    unescaped = re.sub(r"\\[\"'`^~=.]\{?([A-Za-z])\}?", r"\1", value)
    unescaped = re.sub(r"\\[A-Za-z]+\*?(?:\[[^]]*\])?", " ", unescaped)
    unescaped = unescaped.replace("{", "").replace("}", "")
    decomposed = unicodedata.normalize("NFKD", unescaped)
    ascii_like = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^\w\s]", " ", ascii_like.casefold()).split())


def _candidate_title(candidate: Mapping[str, Any]) -> str:
    title = candidate.get("title") or candidate.get("display_name")
    if isinstance(title, str):
        return title
    if isinstance(title, list) and title and isinstance(title[0], str):
        return title[0]
    return ""


def _candidate_authors(candidate: Mapping[str, Any]) -> list[str]:
    raw = candidate.get("authors") or candidate.get("author") or candidate.get("authorships")
    if not isinstance(raw, list):
        return []
    authors: list[str] = []
    for item in raw:
        if isinstance(item, str):
            authors.append(item)
            continue
        if not isinstance(item, Mapping):
            continue
        nested = item.get("author")
        name = (
            nested.get("display_name")
            if isinstance(nested, Mapping)
            else item.get("name") or item.get("display_name")
        )
        family = item.get("family")
        given = item.get("given")
        if isinstance(family, str):
            authors.append(f"{family}, {given}".rstrip(", ") if isinstance(given, str) else family)
            continue
        if isinstance(name, str):
            authors.append(name)
    return authors


def _candidate_year(candidate: Mapping[str, Any]) -> int | None:
    for key in ("year", "publicationYear", "publication_year"):
        value = candidate.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    for key in ("issued", "published-print", "published-online"):
        value = candidate.get(key)
        if not isinstance(value, Mapping):
            continue
        parts = value.get("date-parts")
        if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
            year = parts[0][0]
            if isinstance(year, int):
                return year
    return None


def _candidate_venue(candidate: Mapping[str, Any]) -> str | None:
    for key in ("venue", "journal", "booktitle"):
        value = candidate.get(key)
        if isinstance(value, str) and value.strip():
            return value
    container = candidate.get("container-title")
    if isinstance(container, list) and container and isinstance(container[0], str):
        return container[0]
    publication_venue = candidate.get("publicationVenue")
    if isinstance(publication_venue, Mapping):
        name = publication_venue.get("name")
        if isinstance(name, str):
            return name
    location = candidate.get("primary_location")
    if isinstance(location, Mapping):
        source = location.get("source")
        if isinstance(source, Mapping):
            name = source.get("display_name")
            if isinstance(name, str):
                return name
    return None


def _candidate_doi(candidate: Mapping[str, Any]) -> str | None:
    raw = candidate.get("doi") or candidate.get("DOI")
    external = candidate.get("externalIds")
    if raw is None and isinstance(external, Mapping):
        raw = external.get("DOI")
    if not isinstance(raw, str) or not raw.strip():
        return None
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", raw.strip(), flags=re.IGNORECASE)


def _candidate_string(candidate: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = candidate.get(key)
        if isinstance(value, (str, int)) and str(value).strip():
            return str(value).strip()
    biblio = candidate.get("biblio")
    if isinstance(biblio, Mapping):
        for key in keys:
            value = biblio.get(key)
            if isinstance(value, (str, int)) and str(value).strip():
                return str(value).strip()
    return None


def _candidate_pages(candidate: Mapping[str, Any]) -> str | None:
    direct = _candidate_string(candidate, "pages", "page")
    if direct:
        return _normalize_pages(direct)
    biblio = candidate.get("biblio")
    if not isinstance(biblio, Mapping):
        return None
    first = biblio.get("first_page")
    last = biblio.get("last_page")
    if isinstance(first, (str, int)) and isinstance(last, (str, int)):
        return _normalize_pages(f"{first}-{last}")
    return None


def _candidate_publisher(candidate: Mapping[str, Any]) -> str | None:
    direct = _candidate_string(candidate, "publisher")
    if direct:
        return direct
    location = candidate.get("primary_location")
    if not isinstance(location, Mapping):
        return None
    source = location.get("source")
    if not isinstance(source, Mapping):
        return None
    publisher = source.get("host_organization_name")
    return publisher if isinstance(publisher, str) and publisher.strip() else None


def _normalize_pages(value: str) -> str:
    return re.sub(r"\s*[-–—]+\s*", "-", value.strip())


def _candidate_arxiv_id(candidate: Mapping[str, Any]) -> str | None:
    raw = candidate.get("arxiv_id")
    external = candidate.get("externalIds")
    if raw is None and isinstance(external, Mapping):
        raw = external.get("ArXiv")
    return raw.strip() if isinstance(raw, str) and raw.strip() else None
