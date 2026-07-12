# 에이전트형 스킬 가이드

English original: [../skill-guide.md](../skill-guide.md).

## 목적과 지원 워크플로

`who-is-adam`은 구현에 근거한 ICML 2026 Main Track PDF 리뷰 보조 도구다. 지원되는 워크플로는 `who_is_adam.cli.review`와 `who_is_adam.review.orchestrator.run_review`에 연결된 경로다. 로컬 PDF 하나를 읽고, 구조를 추출하고, 안전 게이트와 ICML 데스크 리젝트 게이트를 적용하고, 독립 전문 리뷰를 실행하고, 이를 공식 ICML 리뷰 필드로 종합하고, 가능한 경우 공개 선행연구 근거를 비교한 뒤 Markdown 출력을 원자적으로 저장한다.

현재 패키지는 결정적 실행과 테스트를 위한 오프라인/가짜 제공자 경로를 지원한다. 호스팅 LLM 설정 필드는 `who_is_adam.config`에 있지만, 이 체크포인트에서는 호스팅 LLM 클라이언트가 연결되어 있지 않으므로 `run_review`는 호스팅 제공자에 대해 `ReviewOrchestrationError`를 발생시킨다.

## 설치와 CLI 도움말

GitHub 체크아웃에서 Python 3.11+ 가상 환경에 설치합니다.

```bash
git clone https://github.com/kwon/who-is-adam.git
cd who-is-adam
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

OCR은 선택 사항입니다. `python -m pip install -e '.[ocr]'`로 extra를 켜고 Tesseract를 별도로 설치합니다(macOS는 `brew install tesseract`, Debian/Ubuntu Linux는 `sudo apt-get install tesseract-ocr`). `who-is-adam --help`와 `who-is-adam review --help`로 명령 표면을 확인합니다.

## 환경 설정

현재 구현된 경로에서는 `WHO_IS_ADAM_OFFLINE=true`를 설정하거나 `--offline`을 전달합니다. 모든 CLI 리뷰 실행에서 `--llm-policy`와 `--code-of-conduct-ack`를 명시합니다. Hosted 제공자 환경 변수는 `ReviewConfig`가 파싱할 수 있지만, 이 체크포인트에서 hosted production review 생성을 활성화하지 않습니다.

## 현재 오프라인/fake 제한

오프라인 fake 리뷰는 오케스트레이션, 거절, 렌더링, 출력 저장을 위한 결정적 계약 테스트입니다. 실제 논문 품질 리뷰가 아니며, hosted LLM 추론을 사용하지 않고 외부 제공자 근거 없음은 fixture 기반 운영 주장 대신 `unavailable`로 기록합니다.

## 입력/출력 계약

CLI 입력은 로컬 PDF 하나와 필수 런타임 확인값이다.

```bash
who-is-adam review paper.pdf --output-dir reviews --llm-policy "<배정된 ICML LLM 정책>" --code-of-conduct-ack --offline
```

`who_is_adam.cli.review`는 오케스트레이션 전에 `--llm-policy` 누락이나 `--code-of-conduct-ack` 누락을 거절한다. 프로그램 호출자는 `run_review(pdf_path=..., output_dir=..., llm_policy=..., code_of_conduct_acknowledged=True, config=ReviewConfig(...))`를 사용한다.

반환 계약은 `who_is_adam.models`의 `ReviewRunResult`다.

- `status=ReviewRunStatus.SAVED`에는 `output_path`가 필요하다.
- `status=ReviewRunStatus.REFUSED`에는 진단 게이트 또는 데스크 체크 객체가 담긴 `refusal`이 필요하다.
- `metadata`는 항상 있으며 LLM 정책 확인, 행동 강령 확인, 제공자 모드, 선택적 고정 타임스탬프, 랜덤 시드를 기록한다.

성공한 Markdown 파일은 `who_is_adam.output.paths.persist_markdown_atomic`에 의해 `<output-dir>/<normalized_title>/<normalized_title>_review_{n}.md` 아래에 저장되며 이전 리뷰를 덮어쓰지 않는다.

## 파이프라인 토폴로지

권위 있는 토폴로지는 `who_is_adam.review.orchestrator.run_review`다.

1. CLI/API 인자와 `ReviewConfig`로 `RuntimeMetadata`를 만든다.
2. `who_is_adam.pdf.extractor.PdfExtractor`로 `PaperStructure`를 추출한다.
3. `who_is_adam.safety.quality_gate.evaluate_pre_review_gates`로 사전 리뷰 게이트를 실행한다.
4. `who_is_adam.icml.desk_reject.run_desk_reject_checks`로 ICML 데스크 리젝트 체크를 실행하고 `blocking_checks` 결과로 차단한다.
5. LLM 클라이언트를 선택한다. 현재는 `LlmProvider.FAKE`만 `FakeLlmClient`를 반환한다.
6. `who_is_adam.review.specialists.run_specialist_reviews`로 독립 전문가들을 실행한다.
7. `who_is_adam.review.synthesis.synthesize_reviews`로 종합한다.
8. `who_is_adam.evidence.prior_work.compare_prior_work_with_openreview`로 선행연구를 비교한다.
9. `who_is_adam.output.markdown.render_review_markdown`로 공식 리뷰 Markdown을 렌더링한다.
10. Markdown을 원자적으로 저장한다.

## 에이전트 로스터

구현된 로스터는 `who_is_adam.review.specialists`의 다섯 역할 튜플 `SPECIALIST_ROLES`와 `who_is_adam.review.synthesis`의 종합기다.

- 분야 분석: `novelty-significance`가 담당한다. 독창성, 선행연구와의 관계, 기여 명확성, 예상 ICML 영향도를 평가한다.
- 방법론: `methodology`가 담당한다. 기술적 타당성, 가정, 증명, 알고리즘, 실험 설계를 평가한다.
- 도메인/선행연구: 주로 `novelty-significance`가 담당하며, 이후 `evidence.prior_work`와 OpenReview 클라이언트가 공개 비교 근거를 추가한다.
- 논리/반론: 모든 전문 리뷰의 `findings`에 분산되어 있고, 종합 단계에서 `conflicts`와 `minority_opinions`로 보존되며 무리하게 합의로 접히지 않는다.
- 재현성/실험: `empirical-evidence`는 데이터셋, 베이스라인, 지표, ablation, 통계, 재현성 근거를 평가한다. `ethics-reproducibility`는 윤리, 한계, 사회적 위험, 산출물 공개, 재현성 주장을 평가한다.
- 발표/독자 부담: `presentation-clarity`가 구성, 글의 명확성, 그림, 표, 표기법, 독자 부담을 평가한다.
- 종합기: `synthesize_reviews`가 완전한 전문 리뷰 집합을 검증하고 LLM에 `SynthesizedReview`를 요청한다.

`SPECIALIST_ROLES`, 전문 역할 수 검증, 종합 검증을 함께 바꾸지 않는 한 추가 라이브 에이전트를 문서화하거나 추가하지 않는다.

## 엄격한 독립성과 종합 규칙

`run_specialist_reviews`는 각 역할을 순차적으로 실행하지만 독립성은 유지한다. LLM에는 논문 근거와 해당 역할의 임무만 전달하며, `safety_context`는 `peer_outputs_visible`을 명시적으로 `false`로 둔다. 반환된 `SpecialistReview`의 `role`이 요청 역할과 다르면 거절하고, 정확히 다섯 개의 고유 역할 이름을 요구한다.

`synthesize_reviews`는 설정된 모든 전문 역할이 정확히 한 번씩 있는지 검증한다. `who_is_adam.review.prompts`의 종합 프롬프트는 합의, 충돌, 신뢰할 수 있는 소수 의견을 보존하라고 지시하며, 모델 계약은 비어 있지 않은 근거를 요구한다. 유지보수자가 로스터를 확장할 때는 프롬프트나 문서보다 먼저 이 검증들을 갱신해야 한다.

## PDF와 프롬프트 인젝션 거절 게이트

첫 번째 강한 거절 지점은 PDF 추출과 사전 리뷰 품질 게이트다. `evaluate_pre_review_gates`는 전문 리뷰가 시작되기 전에 읽을 수 없는 구조, 낮은 품질의 추출, 프롬프트 인젝션 신호를 거절하는 책임을 가진다. 두 번째 강한 거절 지점은 ICML 데스크 체크 단계다. `blocking_checks`는 실패한 Main Track 형식/익명성/범위 체크를 `ReviewRunStatus.REFUSED`로 바꾼다.

프롬프트 계층도 같은 신뢰 경계를 강화한다. `who_is_adam.review.prompts`의 `UNTRUSTED_EVIDENCE_SYSTEM_FRAME`은 LLM에게 논문 텍스트, 참고문헌, 캡션, 메타데이터, 검색된 근거, 전문 리뷰 출력이 신뢰할 수 없는 데이터이며 리뷰 지침을 덮어쓸 수 없다고 알린다. 안전한 거절은 입력이나 실행 환경의 신뢰성 판단이지 논문 품질이 낮다는 판단이 아니다.

## 근거와 출처 규칙

근거 계약은 `who_is_adam.models`에 인코딩되어 있다.

- `EvidenceSpan`은 페이지 번호, 선택적 섹션, 텍스트, 선택적 문자 오프셋을 담는다.
- `Finding`은 최소 하나의 `EvidenceSpan`을 요구한다.
- `SpecialistReview`는 findings와 scores를 요구하고 uncertainty를 담을 수 있다.
- `SynthesizedReview`는 최소 하나의 근거 span과 별도의 consensus/conflict/minority-opinion 필드를 요구한다.
- `ProviderEvidence`, `CitationCheck`, `PriorWorkEvidence`는 외부 제공자 상태와 논문 내부 근거를 구분한다.

Crossref, Semantic Scholar, arXiv, 공개 OpenReview 근거는 출처가 있는 메타데이터로만 사용한다. 누락, rate limit, 비공개, 충돌하는 제공자 결과는 unavailable 또는 uncertain으로 남겨야 하며, 부재를 조작된 주장으로 바꾸지 않는다.

## ICML 공식 출력 필드와 척도

`who_is_adam.output.markdown.OFFICIAL_SECTION_ORDER`는 다음 섹션을 순서대로 렌더링한다. Summary; Strengths And Weaknesses; Questions; Limitations; Soundness; Presentation; Contribution; Rating; Confidence; Ethical Concerns; Reproducibility Notes; Evidence; Consensus; Conflicts; Minority Opinions.

점수 척도는 `who_is_adam.models`의 `ReviewScores`와 `SynthesizedReview`가 강제하고 `SCORE_SCALE_TEXT`가 표시한다.

- Soundness: 1 poor, 2 fair, 3 good, 4 excellent.
- Presentation: 1 poor, 2 fair, 3 good, 4 excellent.
- Contribution: 내부 필드는 `significance`; 1 poor, 2 fair, 3 good, 4 excellent.
- Rating: 내부 필드는 `overall_recommendation`; 1 strong reject부터 6 strong accept까지.
- Confidence: 1 low부터 5 very high까지.

## 구성과 오프라인 모드

`ReviewConfig.from_env`는 `WHO_IS_ADAM_OFFLINE`, LLM 제공자/모델/API/base URL 설정, OpenReview, Semantic Scholar, Crossref, arXiv의 제공자 base URL/API 키, `WHO_IS_ADAM_CROSSREF_MAILTO`, OCR 설정, 고정 타임스탬프, 랜덤 시드를 읽는다. `provider_mode`는 `offline`이 true이거나 LLM 제공자가 `fake`이면 offline이다.

오프라인 모드는 `LlmProvider.FAKE`를 강제하고 결정적 가짜 LLM 동작을 사용하며, 현재 체크포인트에서 문서화된 운영 경로다. 호스팅 제공자 값은 스키마 검증을 받지만 프로덕션 호스팅 리뷰 생성은 아직 구현되어 있지 않다.

## CLI와 Python API 호출 방법

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

스크립트에서 해석할 CLI 종료 코드는 다음과 같습니다.

- `0`: 리뷰 Markdown이 저장되었습니다. `output_path` 또는 `<output-dir>/<normalized_title>/` 아래의 버전 파일을 확인합니다.
- `1`: 구성, 오케스트레이션, 또는 예기치 않은 런타임 실패입니다.
- `2`: 리뷰 Markdown을 쓰기 전 안전한 거절입니다. 품질 게이트, 프롬프트 인젝션 게이트, 차단 ICML desk check가 여기에 포함됩니다.

Desk-check refusal은 도구가 쪽수, 익명성, 파일, 범위, 읽기 가능성 같은 Main Track 제출 형식 또는 정책 조건에서 차단 사유를 찾았다는 뜻입니다. 연구 아이디어가 약하다는 판단이 아니므로, 리뷰 초안을 기대하기 전에 제출/런타임 조건을 고쳐야 합니다.

## 계약을 깨지 않고 전문가를 확장하거나 추가하는 방법

확장은 계약 우선으로 해야 한다.

1. `who_is_adam.review.specialists`의 `SPECIALIST_ROLES`를 바꾼다.
2. 역할 수가 더 이상 정확히 다섯 개가 아니라면 `run_specialist_reviews`를 갱신한다.
3. 새 역할 집합을 기대하고 누락 또는 중복 역할을 계속 거절하도록 `synthesize_reviews` 검증을 갱신한다.
4. `SpecialistReview` findings는 근거 기반으로 유지한다. 근거 없는 판단을 반환할 수 있는 역할을 추가하지 않는다.
5. 오프라인 테스트가 모든 역할을 계속 실행하도록 `FakeLlmClient` fixture나 동작을 갱신한다.
6. 모델과 오케스트레이션 계약을 바꾼 뒤에만 Markdown, 문서, 테스트를 갱신한다.

전문가들이 종합 전에 서로의 초안을 보게 만들지 않는다. 그렇게 하려면 독립성 계약, safety context, 종합 프롬프트, 테스트를 함께 의도적으로 재설계해야 한다.

## 테스트 전략

변경되는 계약 경계 주변에 집중 테스트를 둔다.

- CLI 인자와 거절 동작: 정책 누락, 행동 강령 확인 누락, 거절, 저장된 출력에 대한 `who_is_adam.cli.review` 종료 코드를 테스트한다.
- 오케스트레이션: 가짜/오프라인 제공자로 저장 및 거절 `ReviewRunResult` 분기를 테스트한다.
- 전문가 독립성: 역할 수, 고유성, 역할 불일치 거절, 프롬프트/safety context에 peer output이 없는지를 테스트한다.
- 종합: 역할 누락, 중복 역할, consensus/conflict/evidence 누락 실패, 유효한 `SynthesizedReview` 렌더링을 테스트한다.
- Markdown: `output.markdown`의 공식 섹션 순서와 점수 척도 텍스트를 테스트한다.
- 문서: `tests/test_docs.py`가 영어 기본 문서, 한국어 번역, 상호 링크, 핵심 가이드 제목이 계속 존재하는지 확인하게 유지한다.

전문가, 종합 계약, 출력 계약을 확장한 뒤에는 추상적인 검토에 의존하지 말고 전체 검증 스위트를 실행한다.

```bash
python -m pytest
python -m mypy src/who_is_adam
python -m ruff check .
```

이 명령들은 전문가 역할이나 모델 계약을 바꾼 뒤에도 동작, 타입 계약, lint 규칙이 유지되는지 증명하기 위해 필수다.

## 실패 처리

구성 실패는 리뷰 생성 전에 멈추고 CLI 구성 오류로 표시해야 한다. 사전 리뷰 품질, 프롬프트 인젝션, ICML 데스크 체크 실패는 진단과 함께 `ReviewRunStatus.REFUSED`를 반환해야 하며 리뷰 Markdown을 저장하지 않아야 한다. 호스팅 제공자 선택은 현재 호스팅 클라이언트가 연결되어 있지 않으므로 내부 오케스트레이션 오류로 실패한다. 외부 근거 실패는 조작된 리뷰 내용이 아니라 unavailable provider evidence로 기록해야 한다.

## 전체 흐름 예시

`paper.pdf`가 읽을 수 있는 익명 ICML Main Track PDF이고 운영자가 결정적 오프라인 초안을 원한다고 가정한다.

```bash
who-is-adam review paper.pdf --output-dir reviews --llm-policy "ICML LLM policy reviewed" --code-of-conduct-ack --offline
```

CLI는 환경에서 `ReviewConfig`를 만들고, `--offline` 플래그가 오프라인 모드를 강제한다. `run_review`는 `PaperStructure`를 추출하고, 품질 또는 프롬프트 인젝션 게이트가 실패하면 즉시 거절하며, ICML 데스크 체크가 차단하면 거절한다. 그렇지 않으면 구성된 다섯 전문가를 `FakeLlmClient`로 실행한다. 종합기는 `SynthesizedReview`를 만들고, 가능한 경우 공개 선행연구 비교가 appendices에 추가된다. `render_review_markdown`은 공식 ICML 필드와 메타데이터를 쓰고, `persist_markdown_atomic`은 `reviews/a_study_of_adam/a_study_of_adam_review_1.md` 같은 버전 파일을 저장한다. 같은 제목을 다시 리뷰하면 첫 파일을 덮어쓰지 않고 다음 버전 번호를 사용한다.
