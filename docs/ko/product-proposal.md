# ICML 2026 PDF 리뷰 스킬 제품 제안

English version: [docs/product-proposal.md](../product-proposal.md).

## 현재 상태

이 문서는 `who-is-adam`의 제품 제안서입니다. 이 프로젝트는 문서 우선 제안에서 시작했으며, 현재는 오프라인/fake-provider CLI 경로, PDF 구조 추출, 안전 게이트, ICML desk check, 외부 근거 클라이언트, 격리된 전문 리뷰 생성, 종합, Markdown 렌더링, 버전이 붙은 출력 경로, 계약 테스트가 구현되어 있습니다. hosted LLM 클라이언트는 현재 체크포인트에서 아직 연결되지 않았으므로, 운영상 지원되는 경로는 fake LLM을 사용하는 오프라인 리뷰 생성이며 외부 근거는 결정적 검증을 위해 `unavailable`로 기록됩니다.

## 배경

ICML 2026 Main Track 리뷰는 논문 내용 평가뿐 아니라 제출 형식, 익명성, LLM 사용 정책, 비밀유지, 전문적 행동, 인용 근거 판단을 함께 요구합니다. 현재 구현된 리뷰 schema와 renderer는 ICML 스타일 필드인 `Soundness`, `Presentation`, `Contribution`, `Rating`, `Confidence`를 사용하며, 범위는 각각 1-4, 1-4, 1-4, 1-6, 1-5입니다. 논문 저자의 프롬프트 인젝션은 금지되어 있고, 리뷰어는 배정된 LLM 정책을 따라야 합니다.

## 사용자 문제

리뷰어는 제한된 시간 안에 다음 작업을 반복해야 합니다.

- PDF가 ICML 2026 Main Track 제한에 맞아 보이는지 확인한다.
- 논문 주장과 참고문헌이 실제 근거와 맞는지 점검한다.
- 공개 근거가 없을 때 과거 리뷰 내용을 만들지 않고 선행 연구와 비교한다.
- 리뷰 초안이 구현된 공식 필드 순서와 점수 범위를 벗어나지 않게 한다.
- 논문 내부의 악의적이거나 우발적인 지시문이 LLM 또는 자동화 도구의 행동을 바꾸지 못하게 한다.

## 제안하는 해결책

`who-is-adam`은 로컬 PDF 하나를 입력으로 받아, 안전 게이트와 근거 검사를 통과한 경우에만 ICML Main Track 스타일의 Markdown 리뷰 초안을 저장하는 Python CLI/라이브러리입니다. 도구는 리뷰어에게 구조화된 근거, 위험 신호, 인용 검증 상태, 독립 전문 관점의 평가, 종합 리뷰를 제공합니다. 최종 판단과 제출은 사람이 수행합니다.

구현된 CLI 경로는 fake LLM을 사용하고 외부 제공자 근거를 `unavailable`로 단락 처리하는 결정적 오프라인 실행을 지원합니다. 런타임 오프라인 모드는 fixture 기반 외부 제공자를 사용하지 않습니다. hosted provider 설정은 schema에 존재하지만 hosted 클라이언트는 완성되지 않았으며, production-ready 리뷰 생성 기능으로 설명해서는 안 됩니다.

## 처리 흐름

의도된, 그리고 부분적으로 구현된 흐름은 다음 순서를 따릅니다.

1. **PDF 입력**: 운영자가 로컬 단일 PDF와 출력 디렉터리, 배정된 LLM 정책, 행동 강령 확인을 전달합니다.
2. **구조 추출**: 추출기가 제목, 초록, 섹션, 페이지, 표, 그림, 수식, 참고문헌, 텍스트 span, 추출 품질 지표를 수집합니다.
3. **품질/인젝션 게이트**: 리뷰 전 게이트가 낮은 텍스트 밀도, OCR 품질이 낮은 입력, 손상/암호화 PDF, 프롬프트 인젝션 의심 패턴을 리뷰 생성 전에 거절합니다.
4. **ICML 규정 검사**: desk check가 단일 PDF 가정, 50MB 크기 제한, 메인 본문 8쪽 제한, 익명성 신호, LaTeX 형식 관련 휴리스틱을 평가합니다.
5. **인용 검증**: Crossref, Semantic Scholar, OpenAlex, arXiv가 최대 5개 후보의 제목, 저자, 연도, venue, 출판 세부정보, DOI, arXiv ID를 비교하며 충돌은 `needs_review`로 남깁니다.
6. **선행연구/OpenReview 근거**: prior-work selector는 직접 비교, 개선, 우월성 주장과 공개 OpenReview 근거가 있을 때만 그 근거를 사용하며, 근거가 없으면 unavailable로 남깁니다.
7. **독립 전문 리뷰**: 여러 전문 관점이 서로의 출력을 보지 않고 PDF 근거와 진단만 사용해 평가합니다.
8. **종합**: synthesizer가 합의점, 충돌, 소수 의견, 불확실성을 보존하면서 구현된 공식 필드와 점수 범위로 리뷰를 생성합니다.
9. **Markdown 저장**: 저장된 리뷰는 정규화된 논문 제목 디렉터리에 `<normalized_title>_review_{n}.md` 형식으로 기록되며, `n`은 다음 사용 가능한 버전입니다.

## 리뷰 품질 원칙

- **Evidence before judgment**: 중요한 평가는 논문 span, 페이지, 섹션 또는 외부 출처 상태와 연결합니다.
- **Fail closed**: 안전하지 않거나 읽을 수 없는 입력은 추측 리뷰로 꾸미지 않고 거절합니다.
- **Official schema and scales only**: 생성된 리뷰는 구현된 필드 순서와 점수 범위를 만족해야 합니다.
- **Independent specialists**: 전문 리뷰 prompt는 peer output을 받지 않아 군집 사고와 상호 오염을 줄입니다.
- **Deterministic verification**: 테스트는 fake LLM 동작, 고정 timestamp/seed, ReportLab PDF fixture, `respx` HTTP mock을 사용해 네트워크 없이 실행됩니다. 런타임 오프라인 모드는 fixture 기반 제공자를 사용하지 않고 외부 근거를 `unavailable`로 기록합니다.
- **No fabricated evidence**: API 실패, OpenReview 근거 부재, rate limit은 invented claim으로 바꾸지 않고 unavailable로 기록합니다.

## 사람이 최종 판단한다

이 도구는 리뷰어를 보조하는 분석/초안 생성 도구입니다. ICML 결정, 최종 점수, 리뷰 제출, 이해상충 판단, 윤리적 판단은 사람이 수행해야 합니다. 저장된 Markdown 파일은 검토 가능한 초안이며, 자동 제출물이나 공식 판정이 아닙니다.

## ICML Main Track 한계

- Position Track은 범위 밖입니다.
- 제출 PDF는 단일 파일이며 최대 50MB여야 합니다.
- 메인 본문은 최대 8쪽일 수 있고, 참고문헌과 부록은 그 뒤에 올 수 있습니다.
- 본문/부록 경계가 불명확하면 통과로 꾸미지 않고 `unknown` 또는 경고로 남깁니다.
- 익명성, 형식, 페이지 제한 위반은 자동 거절 가능성이 있는 신호로 표시합니다.
- 현재 렌더링되는 리뷰 출력은 `Soundness`, `Presentation`, `Contribution`, `Rating`, `Confidence`를 사용하며 범위는 1-4, 1-4, 1-4, 1-6, 1-5입니다.

## 비목표

- ICML 또는 OpenReview에 리뷰를 제출하지 않습니다.
- 저자를 대신해 논문을 수정하지 않습니다.
- 공개 근거가 없는 OpenReview 과거 강점이나 약점을 생성하지 않습니다.
- 모든 스캔 PDF를 OCR로 복구한다고 보장하지 않습니다.
- 테스트에서 실제 네트워크, 실제 API 키, 현재 날짜, 로컬 Tesseract 설치에 의존하지 않습니다.
- 현재 체크포인트는 hosted LLM 리뷰 생성이 production-ready라고 주장하지 않습니다.

## 성공 기준 요약

성공한 구현은 다음 조건을 만족합니다.

- 영어 기본 문서가 제품 목적, 워크플로, 거절 의미, 증거 정책, 운영 설정, 출력 이름, 단계별 구현 계획을 설명하고, 한국어 번역은 별도로 보존됩니다.
- 안전/품질 게이트가 리뷰 생성보다 먼저 실행됩니다.
- 인용 및 OpenReview 근거 부재를 추측하지 않고 명시적으로 `unavailable` 처리합니다.
- 구현된 ICML 스타일 필드와 점수 범위를 코드와 테스트에서 검증합니다.
- 오프라인 테스트 모드가 네트워크 호출 없이 결정적 결과를 만듭니다.
