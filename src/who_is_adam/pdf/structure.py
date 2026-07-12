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
_FORMULA_RE = re.compile(r"(?:\$[^$]{2,}\$|\\\(|\\\[|\b(?:argmin|argmax|sum|prod|min|max)\b|[=≤≥].*\(\d+\))")
_YEAR_RE = re.compile(r"\b(18\d{2}|19\d{2}|20\d{2}|2100)\b")
_DOI_RE = re.compile(r"\b10\.\d{4,9}/\S+", re.IGNORECASE)
_ARXIV_RE = re.compile(r"\barXiv:\s*([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)", re.IGNORECASE)


@dataclass(frozen=True)
class PageText:
    """Text extracted from one page."""

    number: int
    text: str


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
    match = re.search(r"(?is)\babstract\b\s*[:\n]?\s*(.+?)(?:\n\s*(?:1\s+)?introduction\b|\n\s*keywords\b|$)", text)
    if match:
        abstract = _collapse(match.group(1))
        if abstract:
            return abstract[:4000]
    first_page = _collapse(pages[0] if pages else "")
    return first_page[:1000] or "No abstract detected."


def extract_tables(pages: list[str]) -> list[TableBlock]:
    return [TableBlock(caption=caption, page=page, span=_span(page, "Table", caption)) for page, kind, caption in _captions(pages) if kind == "table"]


def extract_figures(pages: list[str]) -> list[FigureBlock]:
    return [FigureBlock(caption=caption, page=page, span=_span(page, "Figure", caption)) for page, kind, caption in _captions(pages) if kind == "figure"]


def extract_formulas(pages: list[str]) -> list[FormulaBlock]:
    formulas: list[FormulaBlock] = []
    for page_number, page in enumerate(pages, start=1):
        for line in _lines(page):
            if _FORMULA_RE.search(line):
                label_match = re.search(r"\((\d+)\)\s*$", line)
                label = label_match.group(1) if label_match else None
                formulas.append(FormulaBlock(label=label, page=page_number, span=_span(page_number, "Formula", line[:500])))
    return formulas


def extract_references(pages: list[str]) -> list[ReferenceEntry]:
    text = "\n".join(pages)
    match = re.search(r"(?is)\n\s*(references|bibliography)\s*\n(.+)$", text)
    if not match:
        return []
    raw_entries = re.split(r"\n\s*(?=\[?\d+\]?\s+|[A-Z][A-Za-z-]+,\s+[A-Z])", match.group(2).strip())
    references: list[ReferenceEntry] = []
    reference_page = _page_for_offset(pages, match.start(2))
    for raw in raw_entries:
        entry = _collapse(raw)
        if len(entry) < 10:
            continue
        year = _YEAR_RE.search(entry)
        doi = _DOI_RE.search(entry)
        arxiv = _ARXIV_RE.search(entry)
        references.append(
            ReferenceEntry(
                raw=entry,
                year=int(year.group(1)) if year else None,
                doi=doi.group(0).rstrip(".,") if doi else None,
                arxiv_id=arxiv.group(1) if arxiv else None,
                span=_span(reference_page, "References", entry[:500]),
            )
        )
    return references


def _heading_positions(pages: list[PageText]) -> list[tuple[str, int, int]]:
    headings: list[tuple[str, int, int]] = []
    for page in pages:
        offset = 0
        for line in page.text.splitlines(keepends=True):
            stripped = line.strip()
            if _ABSTRACT_RE.match(stripped) or _REFERENCES_RE.match(stripped) or _SECTION_RE.match(stripped):
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
