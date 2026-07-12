# 운영자 가이드

## 현재 상태

이 가이드는 구현 예정인 `who-is-adam` CLI의 운영 계약을 설명합니다. 현재 체크포인트에서는 문서만 존재하며, 명령 예시는 후속 구현의 목표 동작입니다.

## 설치 전 요구사항

계획된 런타임 및 의존성:

- Python `>=3.11`.
- CLI: `typer`, 터미널 출력: `rich`.
- 모델/계약 검증: `pydantic>=2`.
- PDF 처리: `pymupdf`, `pypdf`.
- HTTP: `httpx`만 사용.
- 참고문헌 파싱/매칭: `bibtexparser`, `rapidfuzz`.
- OCR 선택 기능: Python extra `pytesseract`, `pillow`; 시스템 Tesseract 실행 파일은 별도 설치 후 `PATH` 또는 `TESSERACT_CMD`로 지정.
- 개발/검증: `pytest`, `respx`, `reportlab`, `mypy`, `ruff`.

새 의존성은 후속 구현 체크포인트에서 위 목록에 맞춰 추가되어야 합니다. 특히 HTTP mock은 `respx`만 사용하고, slug 생성은 외부 `python-slugify`가 아니라 내부 path sanitizer로 구현합니다.

## 환경 변수 매트릭스

| Provider | Required env | Optional env | Offline behavior | Failure semantics |
| --- | --- | --- | --- | --- |
| LLM | hosted 제공자에서는 `WHO_IS_ADAM_LLM_PROVIDER`, `WHO_IS_ADAM_LLM_MODEL`, `WHO_IS_ADAM_LLM_API_KEY`; `custom_http`는 `WHO_IS_ADAM_LLM_BASE_URL`도 필요 | `WHO_IS_ADAM_LLM_TIMEOUT_SECONDS` 기본 60, `WHO_IS_ADAM_LLM_MAX_RETRIES` 기본 1 | `WHO_IS_ADAM_OFFLINE=1` 또는 `--offline`이면 fake LLM 사용 | JSON schema 제약 출력이 없거나 검증 실패가 반복되면 설정/내부 오류로 리뷰 저장 안 함 |
| OpenReview | 기본 공개 조회에는 API 키 없음 | `WHO_IS_ADAM_OPENREVIEW_BASE_URL` 기본 `https://api2.openreview.net`, `WHO_IS_ADAM_OPENREVIEW_TIMEOUT_SECONDS`, `WHO_IS_ADAM_OPENREVIEW_MAX_RETRIES`, 향후 필요 시 `WHO_IS_ADAM_OPENREVIEW_API_KEY` | fixture-backed fake client | 공개 근거 없음 또는 API unavailable이면 prior comparison을 `unavailable`로 남기고 과거 장단점 생성 금지 |
| Semantic Scholar | 없음; API 키 없이 낮은 rate limit 사용 가능 | `WHO_IS_ADAM_SEMANTIC_SCHOLAR_API_KEY`, `WHO_IS_ADAM_SEMANTIC_SCHOLAR_BASE_URL` | fixture-backed fake client | 참고문헌 확인 상태를 `verified`, `weak_match`, `not_found`, `metadata_error`, `unavailable` 중 하나로 기록 |
| Crossref | 없음 | `WHO_IS_ADAM_CROSSREF_BASE_URL` 기본 `https://api.crossref.org`, `WHO_IS_ADAM_CROSSREF_MAILTO` 권장 | fixture-backed fake client | 인용 사실 확인 보조로만 사용하며 논문 품질을 결정하지 않음 |
| arXiv | 없음 | `WHO_IS_ADAM_ARXIV_BASE_URL` 기본 `https://export.arxiv.org/api/query` | fixture-backed fake client | arXiv ID/제목/연도 매칭 보조; peer-reviewed 메타데이터가 있으면 그쪽을 우선 |
| OCR/Tesseract | OCR 요청 시 시스템 `tesseract`가 `PATH`에 있거나 `TESSERACT_CMD` 설정 필요 | OCR Python extra `pytesseract`, `pillow` | 테스트는 로컬 Tesseract에 의존하지 않음 | OCR이 요청됐지만 사용할 수 없거나 신뢰도가 낮으면 품질 진단 후 거절 |

공통 HTTP 제공자 동작은 connect timeout 5초, read timeout 20초, total timeout 30초, idempotent GET에 대해 timeout/connection error/HTTP 429/5xx 재시도 2회입니다. 429를 제외한 4xx는 재시도하지 않고 구조화된 provider error로 기록합니다.

## 기본 실행 절차

예정 설치/실행 흐름:

```bash
python -m pip install -e .
who-is-adam review path/to/paper.pdf \
  --output-dir reviews \
  --llm-policy "assigned ICML reviewer-console policy" \
  --code-of-conduct-ack
```

예정 Python 모듈 실행:

```bash
python -m who_is_adam.cli review path/to/paper.pdf \
  --output-dir reviews \
  --llm-policy test-policy \
  --code-of-conduct-ack \
  --offline
```

예정 exit code:

- `0`: 리뷰가 저장됨.
- `2`: 안전/품질/입력 hard gate에서 거절됨.
- `3`: 설정 또는 제공자 capability 오류.
- `4`: 예상하지 못한 내부 오류.

성공 시 출력은 `<output-dir>/<normalized_title>/<normalized_title>_review_{n}.md`에 저장됩니다. 실패 시 공식 리뷰 Markdown은 저장하지 않고, 거절 이유와 근거를 운영자 진단으로 보여주어야 합니다.

## 오프라인/테스트 모드

`WHO_IS_ADAM_OFFLINE=1` 또는 CLI `--offline`은 fake LLM과 fixture 기반 외부 클라이언트를 선택하고 실제 네트워크를 차단합니다. 테스트는 다음 값을 고정해야 합니다.

- run timestamp.
- random seed `0`.
- fake LLM 응답.
- provider diagnostic.
- fixture path와 golden output.

오프라인 모드는 개발 검증과 재현 가능한 golden 테스트를 위한 모드입니다. 실제 리뷰 초안 품질을 보장하는 운영 모드가 아니라, 네트워크와 API 키 없이 계약을 검증하기 위한 모드입니다.

## 거절 사례

예정 운영자-facing 진단 형태:

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

대표 사례:

- **OCR 품질이 낮은 스캔 PDF**: 텍스트 추출량이 부족하고 OCR이 없거나 confidence가 낮으면 `quality_gate` 거절.
- **프롬프트 인젝션 텍스트**: “ignore previous instructions”, “give maximum score”, “do not mention weaknesses”처럼 리뷰 정책을 바꾸려는 본문 신호가 있으면 `prompt_injection` 거절.
- **51MB PDF**: ICML 제한과 입력 정책을 초과하므로 input hard gate 거절.
- **손상/암호화/애매한 PDF**: 페이지 수, 본문, 참고문헌을 안정적으로 읽을 수 없으면 parser/input 거절.
- **LLM JSON schema capability 없음**: provider가 구조화 출력 또는 adapter 검증을 만족하지 못하면 exit code `3` 설정 오류.

거절은 논문에 대한 공식 평가가 아니며, 안전하고 감사 가능한 리뷰를 생성할 수 없다는 실행 판단입니다.

## 결과물 읽는 법

예정 Markdown 리뷰는 ICML Main Track 공식 필드 순서와 점수 범위를 따라야 합니다.

- Soundness: 1-4.
- Presentation: 1-4.
- Significance: 1-4.
- Originality: 1-4.
- Overall Recommendation: 1-6.
- Confidence: 1-5.

본문에는 다음 보조 섹션이 포함될 수 있습니다.

- ICML desk-check 결과: 페이지 제한, 익명성, 형식, 크기 등.
- citation diagnostics: 각 참고문헌의 verified/weak_match/not_found/metadata_error/unavailable 상태.
- prior-work diagnostics: 최대 다섯 개 핵심 비교와 OpenReview 근거 여부.
- runtime metadata: LLM policy 확인, code-of-conduct acknowledgement, provider mode, tool version, fixed timestamp.

## 예시

오프라인 dry run 예정 예시:

```bash
WHO_IS_ADAM_OFFLINE=1 who-is-adam review tests/fixtures/pdfs/valid_icml_text.pdf \
  --output-dir .tmp-reviews \
  --llm-policy test-policy \
  --code-of-conduct-ack \
  --offline
```

프롬프트 인젝션 거절 예정 예시:

```bash
WHO_IS_ADAM_OFFLINE=1 who-is-adam review tests/fixtures/pdfs/prompt_injection.pdf \
  --output-dir .tmp-reviews \
  --llm-policy test-policy \
  --code-of-conduct-ack \
  --offline
# expected exit code: 2
```

## 문제 해결

- API timeout 또는 rate limit은 외부 근거 `unavailable`로 기록하고 가능한 다른 근거로 계속 진행합니다.
- OpenReview 공개 근거가 없으면 과거 장단점 비교를 생성하지 않습니다.
- OCR이 필요한 스캔 PDF에서는 Tesseract 설치와 `TESSERACT_CMD`를 확인합니다.
- hosted LLM을 사용할 때는 모델명, API 키, JSON schema capability를 먼저 확인합니다.
- 본문/부록 경계가 애매하면 통과로 단정하지 말고 `unknown` 또는 경고로 남깁니다.
