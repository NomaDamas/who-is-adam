"""Deterministic PDF text-to-structure mapping heuristics."""

from __future__ import annotations

import re
from dataclasses import dataclass

from who_is_adam.models import (
    EvidenceSpan,
    FigureBlock,
    FormulaBlock,
    ReferenceEntry,
    SectionBlock,
    TableBlock,
)

_SECTION_RE = re.compile(r"^(?:\d+(?:\.\d+)*\s+)?([A-Z][A-Za-z0-9 ,:;()\-/]{2,80})$")
_ABSTRACT_RE = re.compile(r"^abstract\b", re.IGNORECASE)
_REFERENCES_RE = re.compile(r"^(references|bibliography)\b", re.IGNORECASE)
_CAPTION_RE = re.compile(r"^(table|fig(?:ure)?)[\s.]+\d+[:.\-\s]+(.+)$", re.IGNORECASE)
_FORMULA_RE = re.compile(
    r"(?:\$[^$]{2,}\$|\\\(|\\\[|\b(?:argmin|argmax|sum|prod|min|max)\b|[=≤≥].*\(\d+\))"
)
_YEAR_RE = re.compile(r"\b(18\d{2}|19\d{2}|20\d{2}|2100)\b")
_DOI_RE = re.compile(r"\b10\.\d{4,9}/\S+", re.IGNORECASE)
_ARXIV_RE = re.compile(r"\barXiv:\s*([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)", re.IGNORECASE)
_LEADING_REFERENCE_RE = re.compile(r"^\s*(?:\[?\d+\]?\s*[.)]?\s*)")
_GIVEN_RE = r"(?:[A-Z]\.|[A-Z]\.-?[A-Z]\.|[A-Z][a-z'’-]+(?:\s+(?:[A-Z][a-z'’-]+|[A-Z]\.))*)"
_PERSON_RE = rf"[A-Z][A-Za-z'’-]+,\s*{_GIVEN_RE}"
_AUTHOR_PREFIX_RE = re.compile(
    rf"^(?P<authors>{_PERSON_RE}(?:\s+(?:and|&)\s+{_PERSON_RE})*)(?:\.\s+|\s+)(?P<remainder>.+)$"
)
_INITIALS_FIRST_PERSON_RE = r"(?:[A-Z]\.\s*){1,3}[A-Z][A-Za-z'’-]+"
_INITIALS_FIRST_AUTHOR_PREFIX_RE = re.compile(
    rf"^(?P<authors>{_INITIALS_FIRST_PERSON_RE}"
    rf"(?:(?:,\s*(?:and\s+)?|\s+and\s+){_INITIALS_FIRST_PERSON_RE})*)"
    r"\.\s+(?P<remainder>.+)$"
)
_APA_REFERENCE_RE = re.compile(
    r"^(?P<authors>.+?)\s*\((?P<year>18\d{2}|19\d{2}|20\d{2}|2100)\)\.\s*(?P<remainder>.+)$"
)


@dataclass(frozen=True, slots=True)
class PageText:
    """Text extracted from one page."""

    number: int
    text: str


@dataclass(frozen=True, slots=True)
class ParsedReferenceMetadata:
    authors: list[str]
    title: str | None
    venue: str | None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    publisher: str | None = None


def build_sections(pages: list[str]) -> list[SectionBlock]:
    page_texts = [PageText(index + 1, text) for index, text in enumerate(pages)]
    headings = _heading_positions(page_texts)
    if not headings:
        joined = "\n\n".join(text.strip() for text in pages if text.strip())
        return [
            SectionBlock(
                title="Document",
                text=joined or "No extractable text.",
                page_start=1,
                page_end=max(1, len(pages)),
                spans=[_span(1, "Document", joined or "No extractable text.")],
            )
        ]

    sections: list[SectionBlock] = []
    for index, (title, page_number, start) in enumerate(headings):
        next_page = headings[index + 1][1] if index + 1 < len(headings) else len(pages)
        chunks: list[str] = []
        for current in range(page_number, next_page + 1):
            text = pages[current - 1]
            if current == page_number:
                text = text[start:]
            if index + 1 < len(headings) and current == next_page:
                text = text[: headings[index + 1][2]]
            chunks.append(text.strip())
        body = "\n\n".join(chunk for chunk in chunks if chunk).strip() or title
        sections.append(
            SectionBlock(
                title=title,
                text=body,
                page_start=page_number,
                page_end=next_page,
                spans=[_span(page_number, title, body[:500] or title)],
            )
        )
    return sections


def extract_title(pages: list[str]) -> str:
    for line in _lines(pages[0] if pages else ""):
        normalized = line.strip()
        if normalized and not _ABSTRACT_RE.match(normalized) and len(normalized) >= 6:
            return normalized[:200]
    return "Untitled PDF"


def extract_abstract(pages: list[str]) -> str:
    text = "\n".join(pages)
    match = re.search(
        r"(?is)\babstract\b\s*[:\n]?\s*(.+?)(?:\n\s*(?:1\s+)?introduction\b|\n\s*keywords\b|$)",
        text,
    )
    if match:
        abstract = _collapse(match.group(1))
        if abstract:
            return abstract[:4000]
    first_page = _collapse(pages[0] if pages else "")
    return first_page[:1000] or "No abstract detected."


def extract_tables(pages: list[str]) -> list[TableBlock]:
    return [
        TableBlock(caption=caption, page=page, span=_span(page, "Table", caption))
        for page, kind, caption in _captions(pages)
        if kind == "table"
    ]


def extract_figures(pages: list[str]) -> list[FigureBlock]:
    return [
        FigureBlock(caption=caption, page=page, span=_span(page, "Figure", caption))
        for page, kind, caption in _captions(pages)
        if kind == "figure"
    ]


def extract_formulas(pages: list[str]) -> list[FormulaBlock]:
    formulas: list[FormulaBlock] = []
    for page_number, page in enumerate(pages, start=1):
        for line in _lines(page):
            if _FORMULA_RE.search(line):
                label_match = re.search(r"\((\d+)\)\s*$", line)
                label = label_match.group(1) if label_match else None
                formulas.append(
                    FormulaBlock(
                        label=label,
                        page=page_number,
                        span=_span(page_number, "Formula", line[:500]),
                    )
                )
    return formulas


def extract_references(pages: list[str]) -> list[ReferenceEntry]:
    text = "\n".join(pages)
    match = re.search(r"(?is)\n\s*(references|bibliography)\s*\n(.+)$", text)
    if not match:
        return []
    raw_entries = re.split(
        r"\n\s*(?=(?:\[?\d+\]?|\d+[.)])\s+|[A-Z][A-Za-z-]+,\s+[A-Z])",
        match.group(2).strip(),
    )
    references: list[ReferenceEntry] = []
    reference_page = _page_for_offset(pages, match.start(2))
    for raw in raw_entries:
        entry = _collapse(raw)
        if len(entry) < 10:
            continue
        year = _YEAR_RE.search(entry)
        doi = _DOI_RE.search(entry)
        arxiv = _ARXIV_RE.search(entry)
        parsed = _reference_metadata(entry, year=year, doi=doi, arxiv=arxiv)
        references.append(
            ReferenceEntry(
                raw=entry,
                title=parsed.title,
                authors=parsed.authors,
                year=int(year.group(1)) if year else None,
                venue=parsed.venue,
                volume=parsed.volume,
                issue=parsed.issue,
                pages=parsed.pages,
                publisher=parsed.publisher,
                doi=doi.group(0).rstrip(".,;:)]}") if doi else None,
                arxiv_id=arxiv.group(1) if arxiv else None,
                span=_span(reference_page, "References", entry[:500]),
            )
        )
    return references


def _reference_metadata(
    entry: str,
    *,
    year: re.Match[str] | None,
    doi: re.Match[str] | None,
    arxiv: re.Match[str] | None,
) -> ParsedReferenceMetadata:
    cleaned = _LEADING_REFERENCE_RE.sub("", entry)
    if doi:
        cleaned = cleaned.replace(doi.group(0), "")
    cleaned = re.sub(r"\bdoi\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"https?://(?:dx\.)?doi\.org/", "", cleaned, flags=re.IGNORECASE)
    cleaned = _ARXIV_RE.sub("", cleaned).strip(" ,.;()")
    apa_match = _APA_REFERENCE_RE.match(cleaned)
    initials_first = False
    if apa_match:
        authors_text = apa_match.group("authors")
        remainder = apa_match.group("remainder").strip(" ,.;()")
    else:
        author_match = _INITIALS_FIRST_AUTHOR_PREFIX_RE.match(cleaned)
        if author_match:
            initials_first = True
        else:
            author_match = _AUTHOR_PREFIX_RE.match(cleaned)
        if author_match:
            authors_text = author_match.group("authors")
            remainder = _trim_reference_year(author_match.group("remainder"), year).strip(" ,.;")
        else:
            if year:
                cleaned = cleaned[: cleaned.find(year.group(0))]
            authors_text, separator, remainder = cleaned.partition(". ")
            if not separator:
                return ParsedReferenceMetadata([], None, "arXiv" if arxiv else None)
    author_separator = r",\s*(?:and\s+)?|\s+and\s+" if initials_first else r"\s*,?\s*&\s*|\s+and\s+"
    authors = [
        name.strip(" ,") for name in re.split(author_separator, authors_text) if name.strip(" ,")
    ]
    title_text, separator, venue_text = remainder.rpartition(". ")
    if not separator:
        title_text = remainder
        venue_text = ""
    publisher = None
    if _looks_like_publisher(venue_text):
        publisher = venue_text.strip(" ,.;")
        earlier_title, earlier_separator, possible_venue = title_text.rpartition(". ")
        if earlier_separator:
            title_text = earlier_title
            venue_text = possible_venue
        else:
            venue_text = ""
    title = _clean_latex(title_text.strip(" ,.;")) or None
    venue_text = venue_text.strip(" ,.;")
    if title is None:
        return ParsedReferenceMetadata([], None, "arXiv" if arxiv else None)
    venue, volume, issue, pages = _publication_details(venue_text)
    if venue is None and arxiv:
        venue = "arXiv"
    return ParsedReferenceMetadata(authors, title, venue, volume, issue, pages, publisher)


def _publication_details(
    value: str,
) -> tuple[str | None, str | None, str | None, str | None]:
    if not value:
        return None, None, None, None
    match = re.match(
        r"^(?P<venue>.+?),\s*(?P<volume>\d+)"
        r"(?:\((?P<issue>[^)]+)\))?"
        r"(?:\s*[:;,]\s*(?:pp?\.?\s*)?(?P<pages>\d+\s*[-–—]+\s*\d+))?$",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return value, None, None, None
    raw_pages = match.group("pages")
    pages = re.sub(r"\s*[-–—]+\s*", "-", raw_pages) if raw_pages else None
    return match.group("venue").strip(), match.group("volume"), match.group("issue"), pages


def _looks_like_publisher(value: str) -> bool:
    return bool(
        re.search(
            r"\b(?:press|publishing|publishers|springer|elsevier|wiley|routledge)\s*$",
            value.strip(" ,.;"),
            flags=re.IGNORECASE,
        )
    )


def _trim_reference_year(value: str, year: re.Match[str] | None) -> str:
    if year is None:
        return value
    year_text = year.group(0)
    leading = re.sub(rf"^\(?{year_text}\)?[.,]?\s*", "", value)
    if leading != value:
        return leading
    position = value.rfind(year_text)
    return value[:position] if position >= 0 else value


def _clean_latex(value: str) -> str:
    unescaped = re.sub(r"\\[\"'`^~=.]\{?([A-Za-z])\}?", r"\1", value)
    return unescaped.replace("{", "").replace("}", "").strip()


def _heading_positions(pages: list[PageText]) -> list[tuple[str, int, int]]:
    headings: list[tuple[str, int, int]] = []
    for page in pages:
        offset = 0
        for line in page.text.splitlines(keepends=True):
            stripped = line.strip()
            if (
                _ABSTRACT_RE.match(stripped)
                or _REFERENCES_RE.match(stripped)
                or _SECTION_RE.match(stripped)
            ):
                title = re.sub(r"^\d+(?:\.\d+)*\s+", "", stripped).strip()
                if 3 <= len(title) <= 80:
                    headings.append((title, page.number, offset))
            offset += len(line)
    return headings


def _captions(pages: list[str]) -> list[tuple[int, str, str]]:
    captions: list[tuple[int, str, str]] = []
    for page_number, page in enumerate(pages, start=1):
        for line in _lines(page):
            match = _CAPTION_RE.match(line)
            if match:
                kind = "table" if match.group(1).lower() == "table" else "figure"
                captions.append((page_number, kind, _collapse(line)))
    return captions


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _span(page: int, section: str, text: str) -> EvidenceSpan:
    return EvidenceSpan(page=max(1, page), section=section, text=text or section)


def _page_for_offset(pages: list[str], offset: int) -> int:
    cursor = 0
    for index, page in enumerate(pages, start=1):
        cursor += len(page) + 1
        if cursor >= offset:
            return index
    return max(1, len(pages))
