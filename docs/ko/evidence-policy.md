# 증거 및 안전 정책

English version: [docs/evidence-policy.md](../evidence-policy.md).

## 현재 상태

이 문서는 `who-is-adam`의 증거 처리와 안전 거절 정책을 정의합니다. 현재 코드는 신뢰 경계, PDF 품질 검사, 프롬프트 인젝션 거절, 인용/선행연구 근거 모델, 오프라인 provider 동작, schema 검증 리뷰 출력의 핵심 버전을 구현합니다. hosted LLM provider는 이 체크포인트에서 구성 수준에만 남아 있습니다.

## 신뢰 경계

다음 입력은 모두 신뢰 경계 밖에 있습니다.

- 제출 PDF에서 추출한 텍스트, 표, 그림 캡션, 수식 주변 텍스트, 참고문헌.
- PDF 안에 포함된 자연어 명령, 코드 블록, 링크, 주석, 메타데이터.
- Crossref, Semantic Scholar, OpenAlex, arXiv, OpenReview에서 받은 외부 응답.
- LLM provider의 원시 응답.

신뢰 경계 밖의 데이터는 시스템 정책, 리뷰어 지침, 출력 schema, 점수 범위, 안전 게이트를 변경할 수 없습니다. PDF 본문은 항상 인용된 근거로만 사용되며, 실행 지시로 해석하지 않습니다.

## PDF 근거

PDF 내부 근거는 추출이 허용하는 한 다음 정보를 포함해야 합니다.

- page 번호.
- section 제목 또는 `None`.
- 인용 텍스트 span.
- `char_start`/`char_end`처럼 추출된 위치 정보.
- 근거 출처 범주: title, abstract, body, table, figure, formula, reference.

논문 주장에 대한 리뷰 문장은 가능한 경우 PDF span과 연결되어야 합니다. 근거가 약하거나 본문/부록 경계가 불명확하면 확정 표현 대신 불확실성을 보존합니다.

## 외부 메타데이터 근거

Crossref, Semantic Scholar, OpenAlex, arXiv는 참고문헌 사실 확인 보조로 사용합니다.

- 제목, 저자, 연도, venue, volume, issue, pages, publisher, DOI, arXiv ID 일치 여부를
  확인합니다.
- 검색 후보를 최대 5개까지 비교하고 첫 번째 결과를 그대로 신뢰하지 않고 제목 유사도가
  가장 높은 후보를 선택합니다.
- 값이 존재할 때 연도와 식별자는 정확히 일치해야 하며, 저자 성씨 중첩은 최소 30%여야
  하고, venue 메타데이터도 호환되어야 합니다. 제목만 일치해서는 `verified`가 아닙니다.
- 상태는 `verified`, `weak_match`, `needs_review`, `not_found`, `metadata_error`,
  `unavailable` 같은 명시적 값으로 표현합니다.
- 외부 메타데이터는 논문 품질 점수를 직접 결정하지 않습니다.
- API timeout, rate limit, connection error는 증거가 존재하지 않는다는 증명이 아니라 provider unavailable 진단입니다.

서로 다른 provider가 충돌하면 `needs_review`와 함께 충돌 자체를 진단에 남깁니다. 임의로
더 편한 값을 선택해 확정 사실처럼 쓰지 않습니다. 정규화된 DOI, arXiv ID 또는 제목과
연도로 중복 참고문헌을 탐지합니다. 검증기는 차이를 보고하지만 원고를 수정하지 않습니다.

## OpenReview 근거 제한

OpenReview는 공개 근거가 있을 때만 선행연구 맥락을 보조할 수 있습니다.

- 공개 OpenReview 근거가 없으면 `openreview_evidence=None` 및 comparison status `unavailable`로 남깁니다.
- API가 실패하거나 접근이 제한되면 unavailable/warning 진단으로 기록하고 과거 강점이나 약점을 생성하지 않습니다.
- 비공개 리뷰, 추정된 리뷰 히스토리, 모델이 상상한 평판 정보는 사용할 수 없습니다.
- OpenReview 근거는 제출 논문 심사의 보조 맥락일 뿐, 현재 논문의 공식 평가를 자동 결정해서는 안 됩니다.

## 프롬프트 인젝션 처리

저자 PDF 안의 모든 텍스트는 비신뢰 입력입니다. 다음 유형의 문구는 프롬프트 인젝션 신호입니다.

- 이전 지시를 무시하라는 요청.
- 리뷰어, 시스템, LLM에게 특정 점수나 결론을 강제하는 요청.
- 약점 언급 금지, 숨겨진 정책 노출, 도구 설정 변경, 외부 URL 실행을 지시하는 문구.
- 리뷰 양식이나 안전 정책을 PDF 본문 명령으로 덮어쓰려는 시도.

의심 신호가 임계값을 넘으면 리뷰 생성을 중단하고 거절 진단을 반환합니다. 프롬프트 인젝션 거절은 저자 의도에 대한 징벌적 판단이 아니라 리뷰 무결성을 보호하기 위한 fail-closed 동작입니다.

## 파싱/OCR 품질 기준

품질 게이트는 최소한 다음 신호를 고려해야 합니다.

- 페이지별 텍스트 밀도.
- 추출 가능한 title/abstract/sections/references 존재 여부.
- 암호화, 손상, 페이지 수 확인 실패.
- OCR 요청 시 Tesseract 사용 가능 여부와 confidence.
- 표/그림/수식/참고문헌 추출의 충분성.

품질이 임계값 아래이면 도구는 빈약한 추출 결과를 실제 리뷰처럼 꾸미지 않습니다. OCR은 선택 기능이며 모든 스캔을 복구한다고 약속하지 않습니다. OCR이 불가하거나 신뢰도가 낮으면 올바른 동작은 거절입니다.

## LLM 사용 정책 기록

런타임 메타데이터는 다음 사실을 기록해야 합니다.

- 리뷰어가 제공한 `llm_policy` 이름 또는 원문.
- `code_of_conduct_acknowledged=True`가 제공되었는지 여부.
- provider mode: fake/offline, OpenAI, Anthropic, custom HTTP 등.
- official docs checked timestamp 또는 문서 버전.
- tool version, 고정 run timestamp, 테스트 seed 같은 재현성 정보.

LLM provider는 JSON-schema-constrained output을 지원하거나 adapter 수준 Pydantic 검증을 통과해야 합니다. schema-invalid 응답이 재시도 후에도 계속되면 공식 리뷰 Markdown을 저장하지 않아야 합니다.

## 공식 ICML 출력 제한

현재 renderer와 schema는 구현된 official-style 필드와 범위를 강제합니다.

- Soundness: 1-4.
- Presentation: 1-4.
- Contribution: 1-4.
- Rating: 1-6.
- Confidence: 1-5.

LLM이 범위를 벗어난 점수나 필수 섹션 누락을 반환하면 synthesis는 잘못된 값을 조용히 보정해 저장하지 말고 실패해야 합니다.
