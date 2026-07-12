# ICML 2026 PDF Review Skill Product Proposal

Korean translation: [docs/ko/product-proposal.md](ko/product-proposal.md).

## Current status

This document is the product proposal for `who-is-adam`. The project began as a docs-first proposal and now includes implemented checkpoints for the offline/fake-provider CLI path, PDF structure extraction, safety gates, ICML desk checks, external evidence clients, isolated specialist review generation, synthesis, Markdown rendering, versioned output paths, and contract tests. Hosted LLM clients are still not wired in the current checkpoint, so the operationally supported path is offline review generation with a fake LLM while external evidence is recorded as `unavailable` for deterministic validation.

## Background

ICML 2026 Main Track reviewing requires more than assessing paper content. Reviewers must also reason about submission format, anonymity, LLM-use policy, confidentiality, professional conduct, and citation evidence. The currently implemented review schema and renderer use the ICML-style fields `Soundness`, `Presentation`, `Contribution`, `Rating`, and `Confidence`, with ranges 1-4, 1-4, 1-4, 1-6, and 1-5 respectively. Prompt injection from paper authors is prohibited, and reviewers must follow the LLM policy assigned to them.

## User problem

Reviewers repeatedly need to do the following under time pressure:

- Check whether a PDF appears to satisfy ICML 2026 Main Track limits.
- Verify that paper claims and references match actual evidence.
- Compare against prior work without inventing past-review content when public evidence is unavailable.
- Keep review drafts within the implemented official field order and score ranges.
- Prevent malicious or accidental instructions inside the paper from changing LLM or automation behavior.

## Proposed solution

`who-is-adam` is a Python CLI/library that accepts one local PDF and saves an ICML Main Track-style Markdown review draft only after the input passes safety gates and evidence checks. The tool gives reviewers structured evidence, risk signals, citation verification status, independent specialist perspectives, and a synthesized review. Final judgment and submission remain human responsibilities.

The implemented CLI path supports deterministic offline runs with a fake LLM while external provider evidence short-circuits to `unavailable`; runtime offline mode does not use fixture-backed external providers. Hosted provider configuration exists in the schema, but hosted clients are not complete and should not be presented as production-ready review generation.

## Processing flow

The intended and partially implemented flow is:

1. **PDF input**: The operator provides one local PDF, an output directory, the assigned LLM policy, and a code-of-conduct acknowledgement.
2. **Structure extraction**: The extractor collects title, abstract, sections, pages, tables, figures, formulas, references, text spans, and extraction-quality metrics.
3. **Quality/injection gates**: The pre-review gates reject low text density, OCR-poor inputs, damaged or encrypted PDFs, and suspected prompt-injection patterns before review generation.
4. **ICML rule checks**: Desk checks evaluate single-PDF assumptions, 50 MB size limit, 8-page main-body limit, anonymity signals, and LaTeX-format-related heuristics.
5. **Citation verification**: Crossref, Semantic Scholar, OpenAlex, and arXiv compare up to five candidates across title, authors, year, venue, publication details, DOI, and arXiv ID; conflicts remain `needs_review`.
6. **Prior-work/OpenReview evidence**: The prior-work selector uses direct comparison, improvement, or superiority claims and uses public OpenReview evidence only when it exists; missing evidence remains unavailable.
7. **Independent specialist reviews**: Multiple specialist perspectives evaluate the paper using PDF evidence and diagnostics without seeing each other's outputs.
8. **Synthesis**: The synthesizer preserves consensus, conflicts, minority opinions, and uncertainty while producing the implemented official fields and score ranges.
9. **Markdown persistence**: The saved review is written under a normalized-title directory as `<normalized_title>_review_{n}.md`, where `n` is the next available version.

## Review quality principles

- **Evidence before judgment**: Important assessments should be tied to PDF spans, pages, sections, or external-source status.
- **Fail closed**: Unsafe or unreadable inputs are refused instead of being turned into speculative reviews.
- **Official schema and scales only**: Generated reviews must satisfy the implemented field order and score ranges.
- **Independent specialists**: Specialist prompts do not receive peer outputs, reducing groupthink and cross-contamination.
- **Deterministic verification**: Tests use fake LLM behavior, fixed timestamp/seed values, ReportLab PDF fixtures, and `respx` HTTP mocks so they can run without network access; runtime offline mode records external evidence as `unavailable` instead of using fixture-backed providers.
- **No fabricated evidence**: API failures, missing OpenReview evidence, or rate limits are recorded as unavailable rather than converted into invented claims.

## Humans make the final judgment

This tool is an analysis and drafting aid for reviewers. ICML decisions, final scores, review submission, conflict-of-interest judgment, and ethical judgment must be made by humans. A saved Markdown file is a reviewable draft, not an automatic submission or official decision.

## ICML Main Track limits

- Position Track is out of scope.
- The submission PDF is expected to be a single file and no larger than 50 MB.
- The main body may be up to 8 pages; references and appendices may follow.
- If the main-body/appendix boundary is unclear, the tool should record `unknown` or warnings rather than pretending the paper passed.
- Anonymity, format, and page-limit violations are surfaced as possible automatic-rejection signals.
- Current rendered review output uses `Soundness`, `Presentation`, `Contribution`, `Rating`, and `Confidence` with ranges 1-4, 1-4, 1-4, 1-6, and 1-5.

## Non-goals

- The tool does not submit reviews to ICML or OpenReview.
- It does not edit papers on behalf of authors.
- It does not generate historical OpenReview strengths or weaknesses without public evidence.
- It does not guarantee OCR recovery for every scanned PDF.
- It does not depend on real network access, real API keys, the current date, or a local Tesseract installation in tests.
- The current checkpoint does not claim hosted LLM review generation is production-ready.

## Success criteria summary

A successful implementation satisfies these conditions:

- English default documentation explains the product purpose, workflow, refusal meaning, evidence policy, operational configuration, output naming, and staged implementation plan, with Korean translations preserved separately.
- Safety and quality gates run before review generation.
- Citation and OpenReview evidence absence is represented explicitly as `unavailable` instead of guessed.
- The implemented ICML-style fields and score ranges are validated in code and tests.
- Offline test mode produces deterministic results without network calls.
