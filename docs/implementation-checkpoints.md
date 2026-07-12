# Implementation Checkpoints and Git Commit Plan

Korean translation: [docs/ko/implementation-checkpoints.md](ko/implementation-checkpoints.md).

## Current status

This document records the approved staged implementation plan in English. The original Korean checkpoint document remains intact as the Korean translation. The repository has progressed beyond the first docs-only checkpoint: product code and tests now exist for the offline CLI/review path, PDF extraction, safety gates, desk checks, evidence clients, specialist/synthesis review flow, Markdown rendering, and output path versioning.

## Git commit plan

Each commit should be made only after that checkpoint's verification commands pass. The table aligns approved checkpoints, file scope, verification commands, expected behavior, and commit messages.

| Checkpoint | Files | Verification command | Expected behavior | Commit message |
| --- | --- | --- | --- | --- |
| 1. Korean docs-first product proposal | `README.md`, `docs/ko/product-proposal.md`, `docs/ko/operator-guide.md`, `docs/ko/evidence-policy.md`, `docs/ko/implementation-checkpoints.md` | See `Checkpoint 1 verification command` below | Required Korean headings/phrases exist, and this commit contains no `src/` product implementation | `docs: describe ICML review skill proposal in Korean` |
| 2. Project skeleton, config, contracts, provider interfaces | `pyproject.toml`, `.env.example`, `src/who_is_adam/__init__.py`, `src/who_is_adam/cli.py`, `src/who_is_adam/config.py`, `src/who_is_adam/models.py`, `src/who_is_adam/llm/base.py`, `tests/test_review_schema.py`, `tests/test_docs.py` | `python -m pytest tests/test_docs.py tests/test_review_schema.py`; `python -m mypy src/who_is_adam`; `python -m ruff check .` | Schema rejects out-of-range ICML scores and missing official sections; config validates fake/offline mode and JSON-schema capability requirements; documentation tests continue to pass | `feat: add typed review skill skeleton` |
| 3. Deterministic fixtures and PDF extraction | `tests/conftest.py`, `tests/fixtures/build_fixtures.py`, `tests/fixtures/pdfs/*.pdf`, `src/who_is_adam/pdf/extractor.py`, `src/who_is_adam/pdf/ocr.py`, `src/who_is_adam/pdf/structure.py`, part of `tests/test_quality_gate.py` | `python tests/fixtures/build_fixtures.py`; `python -m pytest tests/test_quality_gate.py`; `python -m mypy src/who_is_adam`; `python -m ruff check .` | ReportLab fixtures regenerate deterministically; valid fixtures expose title/sections/pages/tables/figures/formulas/references; the low-text fixture exposes low extraction-quality metrics | `feat: extract deterministic PDF structure` |
| 4. Safety gates and ICML desk checks | `src/who_is_adam/safety/quality_gate.py`, `src/who_is_adam/safety/prompt_injection.py`, `src/who_is_adam/icml/constants.py`, `src/who_is_adam/icml/desk_reject.py`, `tests/test_prompt_injection.py`, `tests/test_desk_reject.py`, expanded `tests/test_quality_gate.py` | `python -m pytest tests/test_quality_gate.py tests/test_prompt_injection.py tests/test_desk_reject.py`; `python -m mypy src/who_is_adam`; `python -m ruff check .` | Low-quality/OCR-poor fixtures are refused; prompt-injection fixtures are refused before review generation; over-8-page and anonymity-violation fixtures produce rule-specific evidence; official scale/order constants exist | `feat: enforce safety and ICML desk checks` |
| 5. External evidence clients and no-network citation tests | `src/who_is_adam/evidence/citations.py`, `src/who_is_adam/evidence/crossref.py`, `src/who_is_adam/evidence/semantic_scholar.py`, `src/who_is_adam/evidence/arxiv.py`, `src/who_is_adam/evidence/openreview.py`, `src/who_is_adam/evidence/prior_work.py`, `tests/fixtures/http/*.json`, `tests/test_citations.py`, `tests/test_prior_work.py` | `WHO_IS_ADAM_OFFLINE=1 python -m pytest tests/test_citations.py tests/test_prior_work.py`; `python -m mypy src/who_is_adam`; `python -m ruff check .` | `respx` intercepts all HTTP; there is no real network; citation status is deterministic; prior-work selector returns up to five direct comparison claims; missing OpenReview evidence remains `unavailable` without invented strengths/weaknesses | `feat: verify citations and prior-work evidence offline` |
| 6. Specialist reviews, synthesis, and prompt boundaries | `src/who_is_adam/review/prompts.py`, `src/who_is_adam/review/specialists.py`, `src/who_is_adam/review/synthesis.py`, expanded `src/who_is_adam/llm/base.py`, `tests/test_orchestrator_success.py` or focused helper tests | `WHO_IS_ADAM_OFFLINE=1 python -m pytest tests/test_review_schema.py tests/test_orchestrator_success.py`; `python -m mypy src/who_is_adam`; `python -m ruff check .` | Fake LLM returns deterministic role-specific JSON; specialist prompts treat PDF text as untrusted quoted evidence; specialists do not receive peer output; synthesis preserves consensus/conflicts/minority opinions; invalid schema fails | `feat: synthesize isolated specialist reviews` |
| 7. Markdown rendering, paths, orchestrator, and golden outputs | `src/who_is_adam/output/markdown.py`, `src/who_is_adam/output/paths.py`, `src/who_is_adam/review/orchestrator.py`, completed `src/who_is_adam/cli.py`, `tests/golden/success_review.md`, `tests/golden/refusal_prompt_injection.json`, `tests/golden/refusal_quality.json`, `tests/test_output_paths.py`, `tests/test_orchestrator_refusal.py`, completed `tests/test_orchestrator_success.py` | `WHO_IS_ADAM_OFFLINE=1 python -m pytest tests/test_output_paths.py tests/test_orchestrator_refusal.py tests/test_orchestrator_success.py`; `WHO_IS_ADAM_OFFLINE=1 python -m pytest`; `python -m mypy src/who_is_adam`; `python -m ruff check .` | Successful fixtures match the official-section-order Markdown golden; refusal fixtures match golden diagnostics and do not save official reviews; output paths use the internal slug helper and `n=max(existing)+1`; fixed timestamp/seed/provider metadata keeps goldens stable | `feat: render versioned ICML review outputs` |
| 8. Final docs sync and full verification | `README.md`, `docs/ko/operator-guide.md`, `docs/ko/evidence-policy.md`, `docs/ko/implementation-checkpoints.md`, and small test/doc updates needed to match real CLI/env behavior | `WHO_IS_ADAM_OFFLINE=1 python -m pytest`; `python -m mypy src/who_is_adam`; `python -m ruff check .`; `python -m who_is_adam.cli review tests/fixtures/pdfs/valid_icml_text.pdf --output-dir .tmp-reviews --llm-policy test-policy --code-of-conduct-ack --offline`; `python -m who_is_adam.cli review tests/fixtures/pdfs/prompt_injection.pdf --output-dir .tmp-reviews --llm-policy test-policy --code-of-conduct-ack --offline; test $? -eq 2` | Full suite, mypy, and ruff pass; the valid sample saves one review; the prompt-injection sample exits 2 and saves no review; documentation matches actual CLI/env behavior | `docs: finalize operator guide for offline review skill` |

## Checkpoint 1 verification command

Use this docs-only validation when checking that English remains the default documentation surface and Korean content remains a complete translation set.

```bash
python - <<'PY'
from pathlib import Path
required = {
    'README.md': ['Product proposal summary','Safe refusal policy','Evidence policy','Output location and file names'],
    'docs/product-proposal.md': ['Processing flow','Review quality principles','Humans make the final judgment'],
    'docs/operator-guide.md': ['Environment variable matrix','Refusal examples','Offline/test mode'],
    'docs/evidence-policy.md': ['Trust boundary','OpenReview evidence limits','Prompt-injection handling'],
    'docs/implementation-checkpoints.md': ['Git commit plan','Verification command','Commit messages'],
    'docs/skill-guide.md': ['Purpose and supported workflow','Input/output contract','Testing strategy'],
    'docs/ko/README.md': ['제품 제안 요약','안전한 거절 정책','증거 정책','출력 위치와 파일 이름'],
    'docs/ko/product-proposal.md': ['처리 흐름','리뷰 품질 원칙','사람이 최종 판단한다'],
    'docs/ko/operator-guide.md': ['환경 변수 매트릭스','거절 사례','오프라인/테스트 모드'],
    'docs/ko/evidence-policy.md': ['신뢰 경계','OpenReview 근거 제한','프롬프트 인젝션 처리'],
    'docs/ko/implementation-checkpoints.md': ['Git 커밋 계획','검증 명령','커밋 메시지'],
    'docs/ko/skill-guide.md': ['목적과 지원 워크플로','입력/출력 계약','테스트 전략'],
}
for file, needles in required.items():
    text = Path(file).read_text(encoding='utf-8')
    missing = [n for n in needles if n not in text]
    if missing:
        raise SystemExit(f'{file} missing {missing}')
print('english-default bilingual docs checkpoint ok')
PY
```

Expected output:

```text
english-default bilingual docs checkpoint ok
```

## Verification command operating principles

- Do not create a checkpoint commit before that checkpoint's commands pass.
- Tests must not depend on network access, current date, real API keys, or local Tesseract installation.
- `mypy` is required verification.
- `ruff check .` runs for code checkpoints.
- HTTP mocks use `respx` only.
- PDF fixtures are generated deterministically with ReportLab.

## Commit messages

Approved commit messages, in order:

1. `docs: describe ICML review skill proposal in Korean`
2. `feat: add typed review skill skeleton`
3. `feat: extract deterministic PDF structure`
4. `feat: enforce safety and ICML desk checks`
5. `feat: verify citations and prior-work evidence offline`
6. `feat: synthesize isolated specialist reviews`
7. `feat: render versioned ICML review outputs`
8. `docs: finalize operator guide for offline review skill`

## Staged implementation summary

- Documentation first defines product purpose, safe refusal, evidence sources, operational contract, and output names.
- The Python `>=3.11` skeleton and schema then validate the implemented ICML-style score ranges in code.
- Deterministic PDF fixtures and extraction precede safety gates and desk checks.
- External evidence providers are verified with no-network tests, and missing OpenReview evidence is not guessed.
- Independent specialist review and synthesis preserve prompt boundaries.
- The final implementation verifies Markdown persistence, output path versioning, golden outputs, CLI smoke behavior, and documentation sync with actual behavior.
