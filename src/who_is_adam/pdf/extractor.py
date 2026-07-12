"""PDF extraction using PyMuPDF text/layout with pypdf metadata checks."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from who_is_adam.models import ExtractionMetrics, PaperStructure
from who_is_adam.pdf.ocr import NullOcrAdapter, OcrAdapter
from who_is_adam.pdf.structure import (
    build_sections,
    extract_abstract,
    extract_figures,
    extract_formulas,
    extract_references,
    extract_tables,
    extract_title,
)

LOW_TEXT_CHARS = 200


class PdfExtractionError(RuntimeError):
    """Raised when a PDF cannot be opened or mapped into the typed structure."""


class PdfExtractor:
    """Extract text, OCR fallback text, and typed structure from a local PDF."""

    def __init__(self, *, ocr_adapter: OcrAdapter | None = None, low_text_chars: int = LOW_TEXT_CHARS) -> None:
        self.ocr_adapter = ocr_adapter or NullOcrAdapter()
        self.low_text_chars = low_text_chars

    def extract(self, path: str | Path) -> PaperStructure:
        pdf_path = Path(path)
        if pdf_path.suffix.lower() != ".pdf":
            raise PdfExtractionError("input must be a PDF file")
        if not pdf_path.exists():
            raise PdfExtractionError(f"PDF does not exist: {pdf_path}")

        page_count, encrypted = self._read_pypdf_metadata(pdf_path)
        if encrypted:
            raise PdfExtractionError("encrypted PDFs cannot be reviewed")

        pages, ocr_used = self._extract_pages(pdf_path)
        if not pages:
            raise PdfExtractionError("PDF contains no pages")
        if page_count and page_count != len(pages):
            page_count = len(pages)

        metrics = ExtractionMetrics(
            page_count=page_count or len(pages),
            extracted_text_chars=sum(len(page) for page in pages),
            low_text_pages=[index + 1 for index, page in enumerate(pages) if len(page.strip()) < self.low_text_chars],
            ocr_used=ocr_used,
            encrypted=False,
        )
        return PaperStructure(
            title=extract_title(pages),
            abstract=extract_abstract(pages),
            sections=build_sections(pages),
            pages=pages,
            tables=extract_tables(pages),
            figures=extract_figures(pages),
            formulas=extract_formulas(pages),
            references=extract_references(pages),
            extraction_metrics=metrics,
        )

    def _read_pypdf_metadata(self, path: Path) -> tuple[int, bool]:
        try:
            reader = PdfReader(str(path))
            encrypted = bool(reader.is_encrypted)
            if encrypted:
                return 0, True
            return len(reader.pages), False
        except Exception as exc:
            raise PdfExtractionError(f"pypdf could not read PDF metadata: {exc}") from exc

    def _extract_pages(self, path: Path) -> tuple[list[str], bool]:
        try:
            import fitz  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - dependency declared in project
            raise PdfExtractionError("PyMuPDF is required for PDF extraction") from exc

        pages: list[str] = []
        ocr_used = False
        try:
            with fitz.open(path) as document:
                for page_number, page in enumerate(document, start=1):
                    text = page.get_text("text", sort=True).strip()
                    if len(text) < self.low_text_chars:
                        ocr_result = self.ocr_adapter.extract_page(page, page_number=page_number)
                        if ocr_result.text.strip():
                            text = f"{text}\n{ocr_result.text}".strip()
                            ocr_used = True
                    pages.append(text)
        except Exception as exc:
            raise PdfExtractionError(f"PyMuPDF could not extract PDF text: {exc}") from exc
        return pages, ocr_used
