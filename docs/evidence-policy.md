# Evidence and Safety Policy

Korean translation: [docs/ko/evidence-policy.md](ko/evidence-policy.md).

## Current status

This document defines the evidence-handling and safe-refusal policy for `who-is-adam`. The current code implements core versions of the trust boundary, PDF quality checks, prompt-injection refusal, citation/prior-work evidence models, offline provider behavior, and schema-validated review output. Hosted LLM providers remain configuration-level only in this checkpoint.

## Trust boundary

All of the following inputs are outside the trust boundary:

- Text, tables, figure captions, formula-adjacent text, and references extracted from the submitted PDF.
- Natural-language instructions, code blocks, links, comments, and metadata embedded in the PDF.
- External responses from Crossref, Semantic Scholar, OpenAlex, arXiv, and OpenReview.
- Raw LLM provider responses.

Data outside the trust boundary may not change system policy, reviewer instructions, output schemas, score ranges, or safety gates. PDF text is always treated as cited evidence, not as executable instruction.

## PDF evidence

PDF-internal evidence should include as much of the following as extraction allows:

- Page number.
- Section title or `None`.
- Quoted text span.
- Extracted location information such as `char_start` and `char_end`.
- Source category: title, abstract, body, table, figure, formula, or reference.

Review statements about paper claims should be connected to PDF spans where possible. When evidence is weak or the body/appendix boundary is unclear, the review should preserve uncertainty instead of using definitive wording.

## External metadata evidence

Crossref, Semantic Scholar, OpenAlex, and arXiv are used as aids for reference fact-checking.

- Check whether title, authors, year, venue, volume, issue, pages, publisher, DOI, and arXiv ID
  match.
- Compare up to five search candidates and select the best title match instead of trusting the
  first result.
- Require exact year and identifier agreement when available, at least 30% author surname overlap,
  and compatible venue metadata. A title-only match is not sufficient for `verified`.
- Represent status with explicit values such as `verified`, `weak_match`, `needs_review`,
  `not_found`, `metadata_error`, and `unavailable`.
- External metadata does not directly determine paper-quality scores.
- API timeouts, rate limits, and connection errors are provider-unavailable diagnostics, not proof that evidence does not exist.

When providers conflict, record `needs_review` and the conflict in diagnostics. Do not choose the
more convenient value and present it as settled fact. Detect duplicate references by normalized
DOI, arXiv ID, or title and year. The verifier reports differences but does not modify manuscripts.

## OpenReview evidence limits

OpenReview may support prior-work context only when public evidence exists.

- If no public OpenReview evidence is available, keep `openreview_evidence=None` and comparison status `unavailable`.
- If the API fails or access is limited, record unavailable/warning diagnostics and do not generate historical strengths or weaknesses.
- Do not use private reviews, inferred review histories, or model-invented reputation data.
- OpenReview evidence is supporting context for the submitted-paper review; it must not automatically determine the current paper's official assessment.

## Prompt-injection handling

All author-provided PDF text is untrusted input. The following patterns are prompt-injection signals:

- Requests to ignore previous instructions.
- Requests that force a reviewer, system, or LLM into a specific score or conclusion.
- Instructions not to mention weaknesses, to reveal hidden policy, to change tool settings, or to execute external URLs.
- Attempts to overwrite the review form or safety policy through commands in the PDF body.

When suspicious signals exceed the threshold, review generation stops and a refusal diagnostic is returned. Prompt-injection refusal is not a punitive judgment about author intent; it is fail-closed behavior that protects review integrity.

## Parsing and OCR quality criteria

Quality gates should consider at least these signals:

- Text density per page.
- Presence of extractable title, abstract, sections, and references.
- Encryption, corruption, or failure to determine page count.
- Tesseract availability and confidence when OCR is requested.
- Sufficiency of table, figure, formula, and reference extraction.

If quality is below threshold, the tool must not dress up poor extraction as a real review. OCR is optional; the tool does not promise to recover every scan. When OCR is unavailable or low-confidence, the correct behavior is refusal.

## LLM-use policy record

Runtime metadata should record the following facts:

- The reviewer-provided `llm_policy` name or text.
- Whether `code_of_conduct_acknowledged=True` was supplied.
- Provider mode, such as fake/offline, OpenAI, Anthropic, or custom HTTP.
- Official-docs checked timestamp or document version.
- Tool version, fixed run timestamp, test seed, and other reproducibility data.

An LLM provider must support JSON-schema-constrained output or pass adapter-level Pydantic validation. If schema-invalid responses continue after retry, no official review Markdown should be saved.

## Official ICML output limits

The current renderer and schema enforce the implemented official-style fields and ranges:

- Soundness: 1-4.
- Presentation: 1-4.
- Contribution: 1-4.
- Rating: 1-6.
- Confidence: 1-5.

If an LLM returns an out-of-range score or omits required sections, synthesis must fail rather than silently correcting and saving an invalid review.
