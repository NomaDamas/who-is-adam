# 증거 및 안전 정책

## 현재 상태

이 문서는 구현 예정인 증거 처리와 안전 거절 정책을 정의합니다. 현재 체크포인트에서는 정책 문서만 작성하며, 제품 코드가 이미 이를 수행한다고 주장하지 않습니다.

## 신뢰 경계

다음 입력은 모두 신뢰 경계 밖에 있습니다.

- 제출 PDF의 모든 텍스트, 표, 그림 캡션, 수식 주변 텍스트, 참고문헌.
- PDF 안에 포함된 자연어 명령, 코드 블록, 링크, 주석, 메타데이터.
- Crossref, Semantic Scholar, arXiv, OpenReview에서 받은 외부 응답.
- LLM provider의 원시 응답.

신뢰 경계 밖의 데이터는 시스템 정책, 리뷰어 지침, 출력 schema, 점수 범위, 안전 게이트를 변경할 수 없습니다. PDF 본문은 항상 인용된 증거로만 사용되며, 실행 지시로 해석하지 않습니다.

## PDF 근거

PDF 내부 근거는 가능한 한 다음 정보를 포함해야 합니다.

- page 번호.
- section 제목 또는 `None`.
- 인용 텍스트 span.
- char_start/char_end처럼 추출 가능한 위치 정보.
- 해당 근거가 title, abstract, body, table, figure, formula, reference 중 어디에서 왔는지.

논문 주장에 대한 리뷰 문장은 가능한 경우 PDF span과 연결되어야 합니다. 근거가 약하거나 본문/부록 경계가 불명확하면 확정 표현 대신 불확실성을 표시합니다.

## 외부 메타데이터 근거

Crossref, Semantic Scholar, arXiv는 참고문헌 사실 확인 보조로 사용합니다.

- 제목, 저자, 연도, venue, DOI, arXiv ID 일치 여부를 확인합니다.
- 상태는 `verified`, `weak_match`, `not_found`, `metadata_error`, `unavailable` 같은 명시적 값으로 표현합니다.
- 외부 메타데이터는 논문 품질 점수를 직접 결정하지 않습니다.
- API timeout, rate limit, connection error는 증거 부재가 아니라 provider unavailable로 기록합니다.

서로 다른 제공자가 충돌하면 충돌 자체를 진단에 남기고, 임의로 더 편한 값을 선택해 확정 사실처럼 쓰지 않습니다.

## OpenReview 근거 제한

OpenReview는 공개 근거가 있을 때만 선행 연구의 과거 리뷰, 강점, 약점, 비교 정보를 보조하는 데 사용합니다.

- 공개 OpenReview 근거가 없으면 `openreview_evidence=None` 및 comparison `unavailable`로 남깁니다.
- API가 실패하거나 접근이 제한되면 unavailable/warning으로 기록하고 과거 장단점을 생성하지 않습니다.
- 비공개 리뷰, 추정된 리뷰 히스토리, 모델이 상상한 평판 정보는 사용할 수 없습니다.
- OpenReview 근거는 제출 논문 심사의 보조 맥락일 뿐, 현재 논문의 공식 평가를 자동 결정하지 않습니다.

## 프롬프트 인젝션 처리

저자 PDF 안의 모든 텍스트는 비신뢰 입력이므로, 다음 유형의 문구는 프롬프트 인젝션 의심 신호입니다.

- 이전 지시를 무시하라는 요청.
- 리뷰어, 시스템, LLM에게 특정 점수나 결론을 강제하는 요청.
- 약점 언급 금지, 비밀 정책 노출, 도구 설정 변경, 외부 URL 실행을 지시하는 문구.
- 리뷰 양식이나 안전 정책을 PDF 본문 명령으로 덮어쓰려는 시도.

의심 신호가 임계값을 넘으면 리뷰 생성을 중단하고 거절 진단을 반환합니다. 프롬프트 인젝션 거절은 저자 의도에 대한 징벌적 판단이 아니라 리뷰 무결성을 보호하기 위한 fail-closed 동작입니다.

## 파싱/OCR 품질 기준

품질 게이트는 최소한 다음 신호를 고려해야 합니다.

- 페이지별 텍스트 밀도.
- 추출 가능한 title/abstract/section/reference 존재 여부.
- 암호화, 손상, 페이지 수 확인 실패.
- OCR 요청 시 Tesseract 사용 가능 여부와 confidence.
- 표/그림/수식/참고문헌 추출의 충분성.

품질이 임계값 아래이면 도구는 빈약한 추출 결과로 리뷰를 꾸미지 않습니다. OCR이 선택 기능으로 제공되더라도 모든 스캔을 성공적으로 복구한다고 약속하지 않으며, OCR이 불가하거나 신뢰도가 낮으면 거절합니다.

## LLM 사용 정책 기록

런타임 메타데이터는 다음 사실을 기록해야 합니다.

- 리뷰어가 제공한 `llm_policy` 이름 또는 원문.
- `code_of_conduct_acknowledged=True` 여부.
- provider mode: fake/offline, openai, anthropic, custom_http 등.
- official docs checked timestamp 또는 문서 버전.
- tool version, 고정 run timestamp, 테스트 seed 같은 재현성 정보.

LLM provider는 JSON-schema-constrained output 또는 adapter의 Pydantic 검증을 통과해야 합니다. schema-invalid 응답이 재시도 후에도 계속되면 공식 리뷰를 저장하지 않습니다.

## 공식 ICML 출력 제한

도구는 ICML Main Track 공식 점수 범위를 벗어난 값을 허용하지 않아야 합니다.

- Soundness: 1-4.
- Presentation: 1-4.
- Significance: 1-4.
- Originality: 1-4.
- Overall Recommendation: 1-6.
- Confidence: 1-5.

LLM이 범위를 벗어난 점수나 누락된 공식 섹션을 반환하면 합성 리뷰는 실패해야 하며, 잘못된 값을 보정한 척 저장하지 않습니다.
