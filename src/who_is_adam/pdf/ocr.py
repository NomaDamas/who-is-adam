"""Optional OCR adapters for low-text PDF pages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OcrPageResult:
    """OCR text and normalized confidence for one page."""

    text: str
    confidence: float


class OcrAdapter(Protocol):
    """Protocol implemented by optional OCR providers."""

    def extract_page(self, page: object, *, page_number: int) -> OcrPageResult:
        """Return OCR text for a PyMuPDF page-like object."""


class NullOcrAdapter:
    """Deterministic adapter used when OCR is disabled or unavailable."""

    def extract_page(self, page: object, *, page_number: int) -> OcrPageResult:
        del page, page_number
        return OcrPageResult(text="", confidence=0.0)


class TesseractOcrAdapter:
    """Best-effort Tesseract adapter loaded only when explicitly constructed."""

    def __init__(self, *, tesseract_cmd: str | None = None, dpi: int = 200) -> None:
        self.dpi = dpi
        try:
            import pytesseract  # type: ignore[import-not-found]
            from PIL import Image
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise RuntimeError("OCR extra requires pytesseract and pillow") from exc
        self._pytesseract = pytesseract
        self._image_type = Image
        if tesseract_cmd:
            self._pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def extract_page(self, page: object, *, page_number: int) -> OcrPageResult:
        del page_number
        try:
            pixmap = page.get_pixmap(dpi=self.dpi)  # type: ignore[attr-defined]
            image = self._image_type.open(__import__("io").BytesIO(pixmap.tobytes("png")))
            data = self._pytesseract.image_to_data(
                image,
                output_type=self._pytesseract.Output.DICT,
            )
        except Exception as exc:  # pragma: no cover - adapter must fail closed upstream
            raise RuntimeError(f"Tesseract OCR failed: {exc}") from exc

        words: list[str] = []
        confidences: list[float] = []
        for raw_text, raw_confidence in zip(data.get("text", []), data.get("conf", []), strict=False):
            text = str(raw_text).strip()
            if not text:
                continue
            words.append(text)
            try:
                confidence = float(raw_confidence)
            except (TypeError, ValueError):
                continue
            if confidence >= 0:
                confidences.append(confidence / 100.0)

        normalized = max(0.0, min(1.0, sum(confidences) / len(confidences))) if confidences else 0.0
        return OcrPageResult(text=" ".join(words), confidence=normalized)
