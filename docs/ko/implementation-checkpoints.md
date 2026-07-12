# 구현 체크포인트와 Git 커밋 계획

English version: [docs/implementation-checkpoints.md](../implementation-checkpoints.md).

## 현재 상태

이 문서는 승인된 단계별 구현 계획을 한국어로 기록합니다. 저장소는 첫 번째 문서 전용 체크포인트를 넘어 진행되었습니다. 현재는 오프라인 CLI/리뷰 경로, PDF 추출, 안전 게이트, desk check, 근거 클라이언트, specialist/synthesis 리뷰 흐름, Markdown 렌더링, output path versioning을 위한 제품 코드와 테스트가 존재합니다. 현재 localization assignment에서는 테스트, 포매터, Git 명령을 실행하지 않습니다.

## Git 커밋 계획

각 커밋은 해당 체크포인트의 검증 명령이 통과한 뒤에만 수행합니다. 아래 표는 승인된 체크포인트, 파일 범위, 검증 명령, 기대 동작, 커밋 메시지를 일치시킨 계획입니다.

| 체크포인트 | 파일 | 검증 명령 | 기대 동작 | 커밋 메시지 |
| --- | --- | --- | --- | --- |
| 1. Korean docs-first product proposal | `README.md`, `docs/ko/product-proposal.md`, `docs/ko/operator-guide.md`, `docs/ko/evidence-policy.md`, `docs/ko/implementation-checkpoints.md` | 아래 `체크포인트 1 검증 명령` | 필수 한국어 heading/phrase가 모두 있고, 이 커밋에는 `src/` 제품 구현이 없음 | `docs: describe ICML review skill proposal in Korean` |
| 2. Project skeleton, config, contracts, provider interfaces | `pyproject.toml`, `.env.example`, `src/who_is_adam/__init__.py`, `src/who_is_adam/cli.py`, `src/who_is_adam/config.py`, `src/who_is_adam/models.py`, `src/who_is_adam/llm/base.py`, `tests/test_review_schema.py`, `tests/test_docs.py` | `python -m pytest tests/test_docs.py tests/test_review_schema.py`; `python -m mypy src/who_is_adam`; `python -m ruff check .` | schema가 ICML 점수 범위 이탈과 공식 섹션 누락을 거절하고, config가 fake/offline mode 및 JSON-schema capability 요구를 검증하며, 문서 테스트가 계속 통과 | `feat: add typed review skill skeleton` |
| 3. Deterministic fixtures and PDF extraction | `tests/conftest.py`, `tests/fixtures/build_fixtures.py`, `tests/fixtures/pdfs/*.pdf`, `src/who_is_adam/pdf/extractor.py`, `src/who_is_adam/pdf/ocr.py`, `src/who_is_adam/pdf/structure.py`, `tests/test_quality_gate.py` 일부 | `python tests/fixtures/build_fixtures.py`; `python -m pytest tests/test_quality_gate.py`; `python -m mypy src/who_is_adam`; `python -m ruff check .` | ReportLab fixture가 결정적으로 재생성되고, 유효 fixture에서 제목/섹션/페이지/표/그림/수식/참고문헌을 노출하며, low-text fixture는 낮은 추출 품질 지표를 노출 | `feat: extract deterministic PDF structure` |
| 4. Safety gates and ICML desk checks | `src/who_is_adam/safety/quality_gate.py`, `src/who_is_adam/safety/prompt_injection.py`, `src/who_is_adam/icml/constants.py`, `src/who_is_adam/icml/desk_reject.py`, `tests/test_prompt_injection.py`, `tests/test_desk_reject.py`, 확장된 `tests/test_quality_gate.py` | `python -m pytest tests/test_quality_gate.py tests/test_prompt_injection.py tests/test_desk_reject.py`; `python -m mypy src/who_is_adam`; `python -m ruff check .` | 저품질/OCR-poor fixture가 거절되고, 프롬프트 인젝션 fixture가 리뷰 생성 전에 거절되며, 8쪽 초과와 익명성 위반 fixture가 rule-specific 근거를 만들고, 공식 scale/order 상수가 존재 | `feat: enforce safety and ICML desk checks` |
| 5. External evidence clients and no-network citation tests | `src/who_is_adam/evidence/citations.py`, `src/who_is_adam/evidence/crossref.py`, `src/who_is_adam/evidence/semantic_scholar.py`, `src/who_is_adam/evidence/arxiv.py`, `src/who_is_adam/evidence/openreview.py`, `src/who_is_adam/evidence/prior_work.py`, `tests/fixtures/http/*.json`, `tests/test_citations.py`, `tests/test_prior_work.py` | `WHO_IS_ADAM_OFFLINE=1 python -m pytest tests/test_citations.py tests/test_prior_work.py`; `python -m mypy src/who_is_adam`; `python -m ruff check .` | `respx`가 모든 HTTP를 가로채고 실제 네트워크가 없으며, citation status가 결정적이고, prior-work selector가 직접 비교 주장 최대 다섯 개를 반환하며, OpenReview 근거 부재는 invented strength/weakness 없이 `unavailable`로 유지 | `feat: verify citations and prior-work evidence offline` |
| 6. Specialist reviews, synthesis, and prompt boundaries | `src/who_is_adam/review/prompts.py`, `src/who_is_adam/review/specialists.py`, `src/who_is_adam/review/synthesis.py`, 확장된 `src/who_is_adam/llm/base.py`, `tests/test_orchestrator_success.py` 또는 focused helper tests | `WHO_IS_ADAM_OFFLINE=1 python -m pytest tests/test_review_schema.py tests/test_orchestrator_success.py`; `python -m mypy src/who_is_adam`; `python -m ruff check .` | fake LLM이 role별 결정적 JSON을 반환하고, specialist prompt가 PDF text를 untrusted quoted evidence로 취급하며, 각 specialist가 peer output을 받지 않고, synthesis가 합의/충돌/소수 의견을 보존하며, invalid schema는 실패 | `feat: synthesize isolated specialist reviews` |
| 7. Markdown rendering, paths, orchestrator, and golden outputs | `src/who_is_adam/output/markdown.py`, `src/who_is_adam/output/paths.py`, `src/who_is_adam/review/orchestrator.py`, 완성된 `src/who_is_adam/cli.py`, `tests/golden/success_review.md`, `tests/golden/refusal_prompt_injection.json`, `tests/golden/refusal_quality.json`, `tests/test_output_paths.py`, `tests/test_orchestrator_refusal.py`, 완성된 `tests/test_orchestrator_success.py` | `WHO_IS_ADAM_OFFLINE=1 python -m pytest tests/test_output_paths.py tests/test_orchestrator_refusal.py tests/test_orchestrator_success.py`; `WHO_IS_ADAM_OFFLINE=1 python -m pytest`; `python -m mypy src/who_is_adam`; `python -m ruff check .` | 성공 fixture가 official-section-order Markdown golden과 일치하고, 거절 fixture는 golden diagnostic과 일치하며 공식 리뷰를 만들지 않고, output path가 내부 slug helper와 `n=max(existing)+1`을 사용하고, fixed timestamp/seed/provider metadata로 golden이 안정적 | `feat: render versioned ICML review outputs` |
| 8. Final docs sync and full verification | `README.md`, `docs/ko/operator-guide.md`, `docs/ko/evidence-policy.md`, `docs/ko/implementation-checkpoints.md`, 실제 CLI/env를 반영하는 필요한 소규모 test/doc 업데이트 | `WHO_IS_ADAM_OFFLINE=1 python -m pytest`; `python -m mypy src/who_is_adam`; `python -m ruff check .`; `python -m who_is_adam.cli review tests/fixtures/pdfs/valid_icml_text.pdf --output-dir .tmp-reviews --llm-policy test-policy --code-of-conduct-ack --offline`; `python -m who_is_adam.cli review tests/fixtures/pdfs/prompt_injection.pdf --output-dir .tmp-reviews --llm-policy test-policy --code-of-conduct-ack --offline; test $? -eq 2` | 전체 suite, mypy, ruff가 통과하고, valid sample은 리뷰 하나를 저장하며, prompt-injection sample은 exit 2로 종료하고 리뷰를 저장하지 않으며, 문서가 실제 CLI/env 동작과 일치 | `docs: finalize operator guide for offline review skill` |

## 체크포인트 1 검증 명령

부모 에이전트가 원래 한국어 문서 체크포인트를 검증할 때 실행할 문서 전용 검증 명령입니다. 현재 localization assignment에서는 Executor가 테스트, 포매터, Git 명령을 실행하지 않습니다.

```bash
python - <<'PY'
from pathlib import Path
required = {
    'README.md': ['제품 제안 요약','안전한 거절 정책','증거 정책','출력 위치와 파일 이름'],
    'docs/ko/product-proposal.md': ['처리 흐름','리뷰 품질 원칙','사람이 최종 판단한다'],
    'docs/ko/operator-guide.md': ['환경 변수 매트릭스','거절 사례','오프라인/테스트 모드'],
    'docs/ko/evidence-policy.md': ['신뢰 경계','OpenReview 근거 제한','프롬프트 인젝션 처리'],
    'docs/ko/implementation-checkpoints.md': ['Git 커밋 계획','검증 명령','커밋 메시지'],
}
for file, needles in required.items():
    text = Path(file).read_text(encoding='utf-8')
    missing = [n for n in needles if n not in text]
    if missing:
        raise SystemExit(f'{file} missing {missing}')
print('docs checkpoint ok')
PY
```

기대 출력:

```text
docs checkpoint ok
```

## 검증 명령 운영 원칙

- 체크포인트별 명령이 통과하기 전에는 해당 커밋을 만들지 않습니다.
- 테스트는 네트워크, 현재 날짜, 실제 API 키, 로컬 Tesseract 설치에 의존하지 않아야 합니다.
- `mypy`는 필수 검증입니다.
- 코드 체크포인트마다 `ruff check .`를 실행합니다.
- HTTP mock은 `respx`만 사용합니다.
- PDF fixture는 ReportLab으로 결정적으로 생성합니다.

## 커밋 메시지

승인된 커밋 메시지는 다음 순서로 사용합니다.

1. `docs: describe ICML review skill proposal in Korean`
2. `feat: add typed review skill skeleton`
3. `feat: extract deterministic PDF structure`
4. `feat: enforce safety and ICML desk checks`
5. `feat: verify citations and prior-work evidence offline`
6. `feat: synthesize isolated specialist reviews`
7. `feat: render versioned ICML review outputs`
8. `docs: finalize operator guide for offline review skill`

## staged implementation 요약

- 문서가 먼저 제품 목적, 안전 거절, 증거 출처, 운영 계약, 출력 이름을 정의합니다.
- 그 다음 Python `>=3.11` 기반 skeleton과 schema가 구현된 ICML 스타일 점수 범위를 코드로 검증합니다.
- 결정적 PDF fixture와 추출기를 추가한 뒤 안전 게이트와 desk check를 구현합니다.
- 외부 근거 provider는 no-network 테스트로 검증하며, OpenReview 근거 부재를 추측하지 않습니다.
- 독립 specialist review와 synthesis는 prompt boundary를 유지합니다.
- 최종 구현은 Markdown 저장, output path versioning, golden output, CLI smoke 동작, 실제 동작과 문서 동기화를 검증합니다.
