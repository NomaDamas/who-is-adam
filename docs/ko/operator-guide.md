# 운영자 가이드

English version: [docs/operator-guide.md](../operator-guide.md).

## 현재 상태

이 가이드는 현재 `who-is-adam` CLI의 운영 계약을 설명합니다. 오프라인/fake-provider 리뷰 경로는 구현되어 있으며, 유효한 fixture에 대해 결정적 Markdown 리뷰를 저장할 수 있습니다. hosted LLM provider 설정은 구성에 표현되어 있지만 hosted 클라이언트는 현재 체크포인트에서 연결되지 않았습니다. hosted 리뷰 경로 시도는 production-supported 모드가 아니라 설정/내부 capability 오류입니다.

## 설치 전 요구사항

런타임 및 개발 의존성:

- Python `>=3.11`.
- CLI: `typer`; 터미널 출력: `rich`.
- 모델/계약 검증: `pydantic>=2`.
- PDF 처리: `pymupdf`, `pypdf`.
- HTTP: `httpx`만 사용.
- 참고문헌 파싱/매칭: `bibtexparser`, `rapidfuzz`.
- OCR 선택 기능: Python extra `pytesseract`, `pillow`; 시스템 Tesseract 실행 파일은 별도 설치 후 `PATH` 또는 `TESSERACT_CMD`로 지정해야 합니다.
- 개발/검증: `pytest`, `respx`, `reportlab`, `mypy`, `ruff`.

새 의존성은 이 목록과 일치해야 합니다. HTTP mock은 `respx`를 사용하고, slug 생성은 외부 `python-slugify`가 아니라 내부 path sanitizer를 사용합니다.

## 환경 변수 매트릭스

| Provider | Required env | Optional env | Offline behavior | Failure semantics |
| --- | --- | --- | --- | --- |
| LLM | hosted provider는 `WHO_IS_ADAM_LLM_PROVIDER`, `WHO_IS_ADAM_LLM_MODEL`, `WHO_IS_ADAM_LLM_API_KEY`가 필요하며, `custom_http`는 `WHO_IS_ADAM_LLM_BASE_URL`도 필요합니다. 현재 지원되는 리뷰 경로는 fake/offline입니다. | `WHO_IS_ADAM_LLM_TIMEOUT_SECONDS` 기본 60, `WHO_IS_ADAM_LLM_MAX_RETRIES` 기본 1. | `WHO_IS_ADAM_OFFLINE=1` 또는 `--offline`이면 fake LLM을 선택합니다. | JSON schema 제약 출력이 없거나, 검증에 실패하거나, hosted 클라이언트가 연결되지 않았으면 리뷰를 저장하지 않고 설정/capability 오류로 표시합니다. |
| OpenReview | 기본 공개 조회에는 API 키가 필요 없습니다. | `WHO_IS_ADAM_OPENREVIEW_BASE_URL` 기본 `https://api2.openreview.net`; `WHO_IS_ADAM_OPENREVIEW_TIMEOUT_SECONDS`; `WHO_IS_ADAM_OPENREVIEW_MAX_RETRIES`; 향후 필요 시 `WHO_IS_ADAM_OPENREVIEW_API_KEY`. | 외부 provider 근거는 `unavailable`로 단락되며, fixture 기반 런타임 근거를 주장하지 않습니다. | 공개 근거가 없거나 API를 사용할 수 없으면 prior comparison은 `unavailable`로 남기며 과거 강점/약점을 생성하지 않습니다. |
| Semantic Scholar | 없음; API 키가 없으면 낮은 rate limit이 적용될 수 있습니다. | `WHO_IS_ADAM_SEMANTIC_SCHOLAR_API_KEY`, `WHO_IS_ADAM_SEMANTIC_SCHOLAR_BASE_URL`. | 외부 provider 근거는 `unavailable`로 단락되며, fixture 기반 런타임 근거를 주장하지 않습니다. | 참고문헌 상태를 `verified`, `weak_match`, `not_found`, `metadata_error`, `unavailable` 중 하나로 기록합니다. |
| Crossref | 없음. | `WHO_IS_ADAM_CROSSREF_BASE_URL` 기본 `https://api.crossref.org`; `WHO_IS_ADAM_CROSSREF_MAILTO` 권장. | 외부 provider 근거는 `unavailable`로 단락되며, fixture 기반 런타임 근거를 주장하지 않습니다. | 인용 사실 확인 보조로만 사용하며 논문 품질을 결정하지 않습니다. |
| arXiv | 없음. | `WHO_IS_ADAM_ARXIV_BASE_URL` 기본 `https://export.arxiv.org/api/query`. | 외부 provider 근거는 `unavailable`로 단락되며, fixture 기반 런타임 근거를 주장하지 않습니다. | arXiv ID/제목/연도 매칭을 보조하며, peer-reviewed 메타데이터가 있으면 그쪽을 우선합니다. |
| OCR/Tesseract | OCR 요청 시 시스템 `tesseract`가 `PATH`에 있거나 `TESSERACT_CMD`가 설정되어야 합니다. | OCR Python extra `pytesseract`, `pillow`. | 테스트는 로컬 Tesseract에 의존하지 않습니다. | OCR이 요청됐지만 사용할 수 없거나 신뢰도가 낮으면 품질 진단 후 거절합니다. |

공통 HTTP 동작은 connect timeout 5초, read timeout 20초, total timeout 30초를 사용하고, idempotent GET에 대해 timeout/connection error/HTTP 429/5xx에서 2회 재시도해야 합니다. 429를 제외한 4xx는 재시도하지 않고 구조화된 provider error로 기록합니다.

## 기본 실행 절차

저장소에서 작업할 때 editable mode로 설치합니다.

```bash
python -m pip install -e .
```

현재 지원되는 오프라인/fake-provider CLI 경로를 실행합니다.

```bash
who-is-adam review path/to/paper.pdf \
  --output-dir reviews \
  --llm-policy "assigned ICML reviewer-console policy" \
  --code-of-conduct-ack \
  --offline
```

동등한 Python 모듈 실행:

```bash
python -m who_is_adam.cli review path/to/paper.pdf \
  --output-dir reviews \
  --llm-policy test-policy \
  --code-of-conduct-ack \
  --offline
```

Exit code:

- `0`: 리뷰 Markdown이 저장됨.
- `2`: 안전 또는 프롬프트 인젝션 거절을 포함해, 안전/품질/입력/desk-check hard gate에서 리뷰가 거절됨.
- `3`: 설정 또는 provider capability 오류.
- `4`: 예상하지 못한 내부 오류.

성공 시 출력은 `<output-dir>/<normalized_title>/<normalized_title>_review_{n}.md`에 저장됩니다. 실패 시 공식 리뷰 Markdown은 저장하지 않고, 운영자에게 거절 이유와 근거 진단을 보여줍니다.

## 오프라인/테스트 모드

`WHO_IS_ADAM_OFFLINE=1` 또는 CLI `--offline`은 fake LLM을 선택합니다. 오프라인 모드의 외부 provider 근거는 런타임 fixture에 의해 뒷받침되지 않으며, hosted/network 근거는 `unavailable`로 단락되어 테스트가 실제 provider에 의존하지 않게 합니다. 테스트는 다음 값을 고정해야 합니다.

- run timestamp.
- random seed `0`.
- fake LLM 응답.
- unavailable provider 진단.
- golden output 경로.

오프라인 모드는 개발 검증과 재현 가능한 golden 테스트를 위한 모드입니다. 최종 리뷰 품질을 보장하지 않으며, 네트워크와 API 키 없이 계약을 검증하기 위한 모드입니다.

## 거절 사례

운영자-facing 진단은 다음 형태를 따라야 합니다.

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
- **프롬프트 인젝션 텍스트**: “ignore previous instructions”, “give maximum score”, “do not mention weaknesses” 같은 문구는 `prompt_injection` 거절로 이어집니다.
- **51MB PDF**: 포괄적인 50MB ICML/입력 제한을 초과하므로 hard gate에서 거절되고 `2`로 종료됩니다.
- **누락/디렉터리/non-PDF/손상/암호화/애매한 PDF**: 입력이 존재하는 PDF 파일이 아니거나, 50MB를 초과하거나, 페이지 수/본문/참고문헌을 안정적으로 읽을 수 없으면 parser/input 거절로 `2`를 반환합니다.
- **LLM JSON schema capability 없음 또는 hosted 클라이언트 미연결**: provider가 구조화 출력 요구사항을 만족할 수 없으므로 설정/capability 오류로 종료합니다.

거절은 논문에 대한 공식 평가가 아닙니다. 안전하고 감사 가능한 리뷰를 생성할 수 없다는 실행 판단입니다.

## 결과물 읽는 법

Markdown 리뷰는 구현된 ICML 스타일 필드 순서와 점수 범위를 따릅니다.

- Soundness: 1-4.
- Presentation: 1-4.
- Contribution: 1-4.
- Rating: 1-6.
- Confidence: 1-5.

추가 내용에는 다음이 포함될 수 있습니다.

- ICML desk-check 결과: 페이지 제한, 익명성, 형식, 크기, 관련 findings.
- citation diagnostics: 각 참고문헌의 `verified`/`weak_match`/`not_found`/`metadata_error`/`unavailable` 상태.
- prior-work diagnostics: 최대 다섯 개 핵심 비교와 공개 OpenReview 근거 존재 여부.
- runtime metadata: LLM policy 확인, code-of-conduct acknowledgement, provider mode, tool version, fixed timestamp, seed.

## 예시

오프라인 dry run:

```bash
WHO_IS_ADAM_OFFLINE=1 who-is-adam review tests/fixtures/pdfs/valid_icml_text.pdf \
  --output-dir .tmp-reviews \
  --llm-policy test-policy \
  --code-of-conduct-ack \
  --offline
```

프롬프트 인젝션 거절:

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
- OpenReview 공개 근거가 없으면 과거 강점이나 약점을 생성하지 않습니다.
- OCR이 필요한 스캔 PDF에서는 Tesseract 설치와 `TESSERACT_CMD`를 확인합니다.
- hosted LLM 경로를 사용하기 전에는 모델명, API 키, JSON schema capability를 확인합니다. hosted 클라이언트는 현재 체크포인트에서 연결되지 않았습니다.
- 본문/부록 경계가 애매하면 통과로 단정하지 말고 `unknown` 또는 경고로 남깁니다.
