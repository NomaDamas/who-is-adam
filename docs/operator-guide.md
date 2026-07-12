# Operator Guide

Korean translation: [docs/ko/operator-guide.md](ko/operator-guide.md).

## Current status

This guide describes the operational contract for the current `who-is-adam` CLI. The offline/fake-provider review path is implemented and can persist deterministic Markdown reviews for valid fixtures. Hosted LLM provider settings are represented in configuration, but hosted clients are not wired in this checkpoint; attempting a hosted review path is a configuration/internal capability error, not a production-supported mode.

## Prerequisites

Runtime and development dependencies:

- Python `>=3.11`.
- CLI: `typer`; terminal output: `rich`.
- Model and contract validation: `pydantic>=2`.
- PDF processing: `pymupdf`, `pypdf`.
- HTTP: `httpx` only.
- Reference parsing/matching: `bibtexparser`, `rapidfuzz`.
- Optional OCR: Python extra `pytesseract`, `pillow`; the system Tesseract executable must be installed separately and provided through `PATH` or `TESSERACT_CMD`.
- Development/verification: `pytest`, `respx`, `reportlab`, `mypy`, `ruff`.

New dependencies should stay aligned with this list. HTTP mocks should use `respx`, and slug generation should use the internal path sanitizer rather than an external `python-slugify` dependency.

## Environment variable matrix

| Provider | Required env | Optional env | Offline behavior | Failure semantics |
| --- | --- | --- | --- | --- |
| LLM | Hosted providers require `WHO_IS_ADAM_LLM_PROVIDER`, `WHO_IS_ADAM_LLM_MODEL`, and `WHO_IS_ADAM_LLM_API_KEY`; `custom_http` also requires `WHO_IS_ADAM_LLM_BASE_URL`. The current supported review path is fake/offline. | `WHO_IS_ADAM_LLM_TIMEOUT_SECONDS` defaults to 60; `WHO_IS_ADAM_LLM_MAX_RETRIES` defaults to 1. | `WHO_IS_ADAM_OFFLINE=1` or `--offline` selects the fake LLM. | Missing constrained JSON output, failed validation, or unwired hosted clients prevent review persistence and surface as configuration/capability errors. |
| OpenReview | No API key for basic public lookup. | `WHO_IS_ADAM_OPENREVIEW_BASE_URL` defaults to `https://api2.openreview.net`; `WHO_IS_ADAM_OPENREVIEW_TIMEOUT_SECONDS`; `WHO_IS_ADAM_OPENREVIEW_MAX_RETRIES`; future `WHO_IS_ADAM_OPENREVIEW_API_KEY` if needed. | External provider evidence short-circuits to `unavailable`; no fixture-backed runtime evidence is claimed. | If public evidence is absent or the API is unavailable, prior comparison remains `unavailable`; historical strengths/weaknesses must not be generated. |
| Semantic Scholar | None; low rate limits may apply without an API key. | `WHO_IS_ADAM_SEMANTIC_SCHOLAR_API_KEY`, `WHO_IS_ADAM_SEMANTIC_SCHOLAR_BASE_URL`. | External provider evidence short-circuits to `unavailable`; no fixture-backed runtime evidence is claimed. | Reference status is recorded as `verified`, `weak_match`, `not_found`, `metadata_error`, or `unavailable`. |
| Crossref | None. | `WHO_IS_ADAM_CROSSREF_BASE_URL` defaults to `https://api.crossref.org`; `WHO_IS_ADAM_CROSSREF_MAILTO` is recommended. | External provider evidence short-circuits to `unavailable`; no fixture-backed runtime evidence is claimed. | Used only as citation fact-check support; it does not decide paper quality. |
| arXiv | None. | `WHO_IS_ADAM_ARXIV_BASE_URL` defaults to `https://export.arxiv.org/api/query`. | External provider evidence short-circuits to `unavailable`; no fixture-backed runtime evidence is claimed. | Helps match arXiv ID/title/year; peer-reviewed metadata takes precedence when available. |
| OCR/Tesseract | OCR requests require system `tesseract` on `PATH` or `TESSERACT_CMD`. | OCR Python extra `pytesseract`, `pillow`. | Tests do not depend on local Tesseract. | If OCR is requested but unavailable or low-confidence, the tool returns a quality diagnostic and refuses. |

Shared HTTP behavior should use a 5-second connect timeout, 20-second read timeout, 30-second total timeout, and two retries for idempotent GET requests on timeout, connection error, HTTP 429, and 5xx. Non-429 4xx responses are not retried and are recorded as structured provider errors.

## Basic execution procedure

Install in editable mode when working from the repository:

```bash
python -m pip install -e .
```

Run the currently supported offline/fake-provider CLI path:

```bash
who-is-adam review path/to/paper.pdf \
  --output-dir reviews \
  --llm-policy "assigned ICML reviewer-console policy" \
  --code-of-conduct-ack \
  --offline
```

Equivalent module invocation:

```bash
python -m who_is_adam.cli review path/to/paper.pdf \
  --output-dir reviews \
  --llm-policy test-policy \
  --code-of-conduct-ack \
  --offline
```

Exit codes:

- `0`: review Markdown was saved.
- `2`: review was refused by a safety, quality, input, prompt-injection, or desk-check hard gate; refusal returns exit code `2`.
- `3`: configuration or provider capability error.
- `4`: unexpected internal error.

On success, output is saved to `<output-dir>/<normalized_title>/<normalized_title>_review_{n}.md`. On failure, official review Markdown is not saved; the operator receives refusal reasons and supporting diagnostics.

## Offline/test mode

`WHO_IS_ADAM_OFFLINE=1` or CLI `--offline` selects the fake LLM. External provider evidence is not backed by runtime fixtures in offline mode; hosted/network evidence short-circuits to `unavailable` so tests do not depend on real providers. Tests should fix these values:

- Run timestamp.
- Random seed `0`.
- Fake LLM response.
- Unavailable provider diagnostics.
- Golden output path.

Offline mode is for development validation and reproducible golden tests. It is not a guarantee of final review quality; it verifies contracts without network access or API keys.

## Refusal examples

Operator-facing diagnostics should follow this shape:

```json
{
  "status": "refused",
  "category": "quality_gate",
  "reasons": [
    {
      "code": "low_text_density",
      "message": "PDF text extraction is below the review threshold.",
      "evidence": {"pages": [1, 2], "ocr_available": false}
    }
  ],
  "review_saved": false
}
```

Representative cases:

- **Low-quality scanned PDF**: insufficient extracted text and missing or low-confidence OCR lead to `quality_gate` refusal.
- **Prompt-injection text**: phrases such as “ignore previous instructions,” “give maximum score,” or “do not mention weaknesses” are a hard refusal and lead to `prompt_injection` refusal.
- **51 MB PDF**: exceeds the inclusive 50 MB ICML/input limit, so it is refused by a hard gate and exits `2`.
- **Missing, directory, non-PDF, damaged, encrypted, or ambiguous PDF**: if the input is not an existing PDF file, exceeds 50 MB, or page count, body text, or references cannot be read reliably, parser/input refusal exits `2`.
- **Missing LLM JSON-schema capability or unwired hosted client**: the provider cannot satisfy structured-output requirements, so the run exits as a configuration/capability error.

Refusal is not an official evaluation of the paper. It is an execution judgment that a safe, auditable review cannot be generated.

## How to read results

Markdown reviews follow the implemented ICML-style field order and score ranges:

- Soundness: 1-4.
- Presentation: 1-4.
- Contribution: 1-4.
- Rating: 1-6.
- Confidence: 1-5.

Additional content may include:

- ICML desk-check results: page limit, anonymity, format, size, and related findings.
- Citation diagnostics: each reference's `verified`, `weak_match`, `not_found`, `metadata_error`, or `unavailable` status.
- Prior-work diagnostics: up to five key comparisons and whether public OpenReview evidence exists.
- Runtime metadata: LLM policy confirmation, code-of-conduct acknowledgement, provider mode, tool version, fixed timestamp, and seed.

## Examples

Offline dry run:

```bash
WHO_IS_ADAM_OFFLINE=1 who-is-adam review tests/fixtures/pdfs/valid_icml_text.pdf \
  --output-dir .tmp-reviews \
  --llm-policy test-policy \
  --code-of-conduct-ack \
  --offline
```

Prompt-injection refusal:

```bash
WHO_IS_ADAM_OFFLINE=1 who-is-adam review tests/fixtures/pdfs/prompt_injection.pdf \
  --output-dir .tmp-reviews \
  --llm-policy test-policy \
  --code-of-conduct-ack \
  --offline
# expected exit code: 2
```

## Troubleshooting

- API timeouts or rate limits should be recorded as external evidence `unavailable`; continue with other evidence where possible.
- If there is no public OpenReview evidence, do not generate prior strengths or weaknesses.
- For scanned PDFs requiring OCR, check Tesseract installation and `TESSERACT_CMD`.
- Before using a hosted LLM path, verify model name, API key, and JSON-schema capability; hosted clients are not wired in the current checkpoint.
- If the body/appendix boundary is ambiguous, leave an `unknown` or warning rather than asserting the paper passed.
