# Agentic skill guide

Korean translation: [ko/skill-guide.md](ko/skill-guide.md).

## Purpose and supported workflow

`who-is-adam` has two distinct surfaces. The primary surface is the installed Codex or Claude Code skill: the host agent reads one local PDF, performs desk checks, produces independent reviewer lenses and adversarial deliberation, and synthesizes the official ICML review fields into an evidence-grounded Markdown review. This normal skill workflow is prompt-driven and does not require Python.

The secondary surface is the Python CLI wired through `who_is_adam.cli.review` and `who_is_adam.review.orchestrator.run_review`. It provides deterministic offline/fake-provider pipeline diagnostics, extraction gates, and atomic persistence for development and diagnostics. Hosted LLM configuration fields exist, but hosted CLI clients are not wired in this checkpoint.

## Installation and CLI help

Python is optional for normal plugin use. Install it only when developing the CLI or running deterministic offline checks:

```bash
git clone https://github.com/NomaDamas/who-is-adam.git
cd who-is-adam
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

OCR is optional. Enable the extra with `python -m pip install -e '.[ocr]'` and install Tesseract separately (`brew install tesseract` on macOS, or `sudo apt-get install tesseract-ocr` on Debian/Ubuntu Linux). Verify the command surface with `who-is-adam --help` and `who-is-adam review --help`.


## Install as an Agent Skill

The repository ships the skill at `skills/who-is-adam/SKILL.md` and plugin manifests for both Claude Code and Codex. Plugin installation is the recommended path and does not require the Python package.

Claude Code plugin installation:

```text
/plugin marketplace add NomaDamas/who-is-adam
/plugin install who-is-adam
/who-is-adam /path/to/paper.pdf
```

Codex plugin installation:

```bash
codex plugin marketplace add NomaDamas/who-is-adam
codex plugin add who-is-adam@who-is-adam
```

Codex invocation:

```text
Use $who-is-adam to review /path/to/paper.pdf.
```

Manual skill-directory installation remains available for runtimes without plugin support:

```bash
cp -R skills/who-is-adam ~/.claude/skills/who-is-adam
cp -R skills/who-is-adam ~/.codex/skills/who-is-adam
```

For hosts without slash skills, use a natural-language trigger naming the installed skill and local PDF. The `SKILL.md` workflow itself is the review execution surface. The Python CLI is optional and its fake output remains pipeline-test data, not production review quality.

## Environment setup

Normal plugin use requires no environment variables. For optional CLI checks, set `WHO_IS_ADAM_OFFLINE=true` or pass `--offline`, and keep `--llm-policy` plus `--code-of-conduct-ack` explicit. Hosted provider variables do not enable hosted CLI review generation in this checkpoint.

## Current offline/fake limitation

This limitation applies to the optional Python CLI, not the normal installed skill. Offline fake reviews are deterministic pipeline tests for orchestration, refusal, rendering, and output persistence; they are not real paper-quality reviews. Real plugin reviews are performed by the host agent, while hosted production review generation remains unavailable in the CLI. Fake CLI output must not be presented as real paper analysis.

## Input/output contract

CLI input is a single local PDF plus required runtime acknowledgements:

```bash
who-is-adam review paper.pdf --output-dir reviews --llm-policy "<assigned ICML LLM policy>" --code-of-conduct-ack --offline
```

`who_is_adam.cli.review` rejects missing `--llm-policy` or missing `--code-of-conduct-ack` before orchestration. Programmatic callers use `run_review(pdf_path=..., output_dir=..., llm_policy=..., code_of_conduct_acknowledged=True, config=ReviewConfig(...))`.

The return contract is `ReviewRunResult` from `who_is_adam.models`:

- `status=ReviewRunStatus.SAVED` requires `output_path`.
- `status=ReviewRunStatus.REFUSED` requires `refusal` with diagnostic gate or desk-check objects.
- `metadata` is always present and records LLM policy acknowledgement, code-of-conduct acknowledgement, provider mode, optional fixed timestamp, and random seed.

A successful Markdown file is written by `who_is_adam.output.paths.persist_markdown_atomic` under `<output-dir>/<normalized_title>/<normalized_title>_review_{n}.md` without overwriting previous reviews.

## Pipeline topology

The authoritative topology is `who_is_adam.review.orchestrator.run_review`:

1. Build `RuntimeMetadata` from CLI/API arguments and `ReviewConfig`.
2. Extract `PaperStructure` with `who_is_adam.pdf.extractor.PdfExtractor`.
3. Run pre-review gates through `who_is_adam.safety.quality_gate.evaluate_pre_review_gates`.
4. Run ICML desk-reject checks with `who_is_adam.icml.desk_reject.run_desk_reject_checks` and block on `blocking_checks`.
5. Select the LLM client. Only `LlmProvider.FAKE` returns `FakeLlmClient` today.
6. Run independent specialists through `who_is_adam.review.specialists.run_specialist_reviews`.
7. Run synthesis through `who_is_adam.review.synthesis.synthesize_reviews`.
8. Compare prior work through `who_is_adam.evidence.prior_work.compare_prior_work_with_openreview`.
9. Render official review Markdown with `who_is_adam.output.markdown.render_review_markdown`.
10. Persist the Markdown atomically.

## Agent roster

The implemented roster is the five-role tuple `SPECIALIST_ROLES` in `who_is_adam.review.specialists` plus the synthesizer in `who_is_adam.review.synthesis`:

- Field analysis: represented by `novelty-significance`; assesses originality, relation to prior work, contribution clarity, and likely ICML impact.
- Methodology: `methodology`; assesses technical soundness, assumptions, proofs, algorithms, and experimental design.
- Domain/prior-work: also centered in `novelty-significance`, with public comparison evidence added later by `evidence.prior_work` and OpenReview clients.
- Logic/counterargument: spread across all specialist `findings`, then preserved as `conflicts` and `minority_opinions` during synthesis rather than collapsed into consensus.
- Reproducibility/experiments: `empirical-evidence` assesses datasets, baselines, metrics, ablations, statistics, and reproducibility evidence; `ethics-reproducibility` assesses ethics, limitations, risks, artifacts, and reproducibility claims.
- Presentation/reader burden: `presentation-clarity` assesses organization, writing clarity, figures, tables, notation, and reader burden.
- Synthesizer: `synthesize_reviews` validates the complete specialist set and asks the LLM for a `SynthesizedReview`.

Do not document or add extra live agents unless `SPECIALIST_ROLES`, the specialist count validation, and synthesis validation are updated together.

## Strict independence and synthesis rules

`run_specialist_reviews` runs each role sequentially but independently. It sends only the paper evidence and that role's remit to the LLM; the `safety_context` explicitly sets `peer_outputs_visible` to `false`. It rejects any returned `SpecialistReview` whose `role` does not match the requested role, and it requires exactly five unique role names.

`synthesize_reviews` then validates that every configured specialist role is present exactly once. The synthesis prompt in `who_is_adam.review.prompts` says to preserve consensus, conflicts, and credible minority opinions, and the model contract requires non-empty evidence. A maintainer extending the roster must update these validations before changing prompts or documentation.

## PDF and prompt-injection refusal gates

The first hard refusal point is the PDF extraction and pre-review quality gate. `evaluate_pre_review_gates` is responsible for refusing unreadable structure, low-quality extraction, or prompt-injection signals before specialist review starts. The second hard refusal point is the ICML desk-check stage; `blocking_checks` turns failed Main Track format/anonymity/scope checks into `ReviewRunStatus.REFUSED`.

The prompt layer reinforces the same trust boundary. `UNTRUSTED_EVIDENCE_SYSTEM_FRAME` in `who_is_adam.review.prompts` tells the LLM that paper text, references, captions, metadata, retrieved evidence, and specialist outputs are untrusted data and must not override review instructions. A safe refusal is an input or environment reliability decision, not a judgment that the paper is low quality.

## Evidence and provenance rules

The evidence contract is encoded in `who_is_adam.models`:

- `EvidenceSpan` carries page number, optional section, text, and optional character offsets.
- `Finding` requires at least one `EvidenceSpan`.
- `SpecialistReview` requires findings and scores and may carry uncertainty.
- `SynthesizedReview` requires at least one evidence span and separate consensus/conflict/minority-opinion fields.
- `ProviderEvidence`, `CitationCheck`, and `PriorWorkEvidence` distinguish external provider status from paper-internal evidence.

Use Crossref, Semantic Scholar, OpenAlex, arXiv, and public OpenReview evidence as provenance-bearing metadata only. Missing or rate-limited evidence remains `unavailable`; field or provider conflicts remain `needs_review`. Do not turn absence into a fabricated claim.

## ICML official output fields and scales

`who_is_adam.output.markdown.OFFICIAL_SECTION_ORDER` renders these sections in order: Summary; Strengths And Weaknesses; Questions; Limitations; Soundness; Presentation; Contribution; Rating; Confidence; Ethical Concerns; Reproducibility Notes; Evidence; Consensus; Conflicts; Minority Opinions.

The score scales are enforced by `ReviewScores` and `SynthesizedReview` in `who_is_adam.models` and displayed by `SCORE_SCALE_TEXT`:

- Soundness: 1 poor, 2 fair, 3 good, 4 excellent.
- Presentation: 1 poor, 2 fair, 3 good, 4 excellent.
- Contribution: stored as `significance`; 1 poor, 2 fair, 3 good, 4 excellent.
- Rating: stored as `overall_recommendation`; 1 strong reject through 6 strong accept.
- Confidence: 1 low through 5 very high.

## Configuration and offline mode

`ReviewConfig.from_env` reads `WHO_IS_ADAM_OFFLINE`, LLM provider/model/API/base URL settings, provider base URLs/API keys for OpenReview, Semantic Scholar, Crossref, OpenAlex, and arXiv, `WHO_IS_ADAM_CROSSREF_MAILTO`, OCR settings, fixed timestamp, and random seed. `provider_mode` describes external-provider access and is offline only when `offline` is true; selecting the fake LLM alone does not disable citation-provider network access.

Offline mode forces `LlmProvider.FAKE`, uses deterministic fake LLM behavior, and is the documented operational path in the current checkpoint. Hosted provider values are schema-validated, but production hosted review generation is not implemented yet.

## How to invoke CLI and Python API

CLI:

```bash
WHO_IS_ADAM_OFFLINE=true who-is-adam review paper.pdf \
  --output-dir reviews \
  --llm-policy "ICML assigned LLM policy checked" \
  --code-of-conduct-ack \
  --offline
```

Python API:

```python
from pathlib import Path

from who_is_adam.config import ReviewConfig
from who_is_adam.review.orchestrator import run_review

config = ReviewConfig.model_validate({"offline": True})
result = run_review(
    pdf_path=Path("paper.pdf"),
    output_dir=Path("reviews"),
    llm_policy="ICML assigned LLM policy checked",
    code_of_conduct_acknowledged=True,
    config=config,
)
print(result.status, result.output_path)
```

CLI exit codes to interpret in scripts:

- `0`: review Markdown was saved; inspect `output_path` or the versioned file under `<output-dir>/<normalized_title>/`.
- `1`: configuration, orchestration, or unexpected runtime failure.
- `2`: safe refusal before review Markdown is written, including quality gates, prompt-injection gates, or blocking ICML desk checks.

Desk-check refusal means the tool found a blocking Main Track submission-format or policy condition, such as page, anonymity, file, scope, or readability constraints. It is not a claim that the research idea is weak; fix the submission/runtime condition before expecting a review draft.

## How to extend or add a specialist without breaking contracts

Extension must be contract-first:

1. Change `SPECIALIST_ROLES` in `who_is_adam.review.specialists`.
2. Update `run_specialist_reviews` if the count is no longer exactly five.
3. Update `synthesize_reviews` validation so it expects the new role set and still rejects missing or duplicate roles.
4. Keep `SpecialistReview` findings evidence-backed; do not add roles that can return unsupported judgments.
5. Update `FakeLlmClient` fixtures or behavior so offline tests still exercise every role.
6. Update Markdown/docs/tests only after the model and orchestration contracts are changed.

Never make specialists see each other's drafts before synthesis unless the independence contract, safety context, synthesis prompt, and tests are intentionally redesigned together.

## Testing strategy

Use focused tests around the contract seam being changed:

- CLI argument and refusal behavior: test `who_is_adam.cli.review` exit codes for missing policy, missing conduct acknowledgement, refusal, and saved output.
- Orchestration: test saved and refused `ReviewRunResult` branches with fake/offline providers.
- Specialist independence: test role count, uniqueness, role mismatch rejection, and absence of peer outputs in prompts/safety context.
- Synthesis: test missing role, duplicate role, missing consensus/conflict/evidence failures, and valid `SynthesizedReview` rendering.
- Markdown: test official section order and score-scale text from `output.markdown`.
- Documentation: keep `tests/test_docs.py` checking that English defaults, Korean translations, reciprocal links, and key guide headings stay present.

After any specialist, synthesis contract, or output-contract extension, run the full verification suite rather than relying on abstract review:

```bash
python -m pytest
python -m mypy src/who_is_adam
python -m ruff check .
```

These commands are required to prove behavior, type contracts, and lint rules still hold after changing specialist roles or model contracts.

## Failure handling

Configuration failures should stop before review generation and surface as CLI configuration errors. Pre-review quality, prompt-injection, and ICML desk-check failures should return `ReviewRunStatus.REFUSED` with diagnostics and should not save review Markdown. Hosted-provider selection currently fails as an internal orchestration error because hosted clients are not wired. External evidence failures should be recorded as unavailable provider evidence rather than invented review content.

## Worked end-to-end example

Suppose `paper.pdf` is a readable anonymous ICML Main Track PDF and the operator wants a deterministic offline draft:

```bash
who-is-adam review paper.pdf --output-dir reviews --llm-policy "ICML LLM policy reviewed" --code-of-conduct-ack --offline
```

The CLI builds `ReviewConfig` from the environment, then the `--offline` flag forces offline mode. `run_review` extracts `PaperStructure`, rejects immediately if the quality or prompt-injection gate fails, rejects if ICML desk checks block, and otherwise runs the five configured specialists with `FakeLlmClient`. The synthesizer produces a `SynthesizedReview`; public prior-work comparison is appended when available; `render_review_markdown` writes the official ICML fields and metadata; `persist_markdown_atomic` saves a versioned file such as `reviews/a_study_of_adam/a_study_of_adam_review_1.md`. If the same title is reviewed again, the next version number is used instead of overwriting the first file.
