# who-is-adam

English default docs: [README](../../README.md), [product proposal](../product-proposal.md), [operator guide](../operator-guide.md), [evidence policy](../evidence-policy.md), [implementation checkpoints](../implementation-checkpoints.md), [skill guide](../skill-guide.md). 한국어 문서: [제품 제안](product-proposal.md), [운영자 가이드](operator-guide.md), [증거 정책](evidence-policy.md), [구현 체크포인트](implementation-checkpoints.md), [스킬 가이드](skill-guide.md)

## 제품 제안 요약

`who-is-adam`은 ICML 2026 Main Track 논문 PDF를 대상으로 하는 리뷰 보조 스킬입니다. 현재 상태는 **문서 우선 제안 단계에서 구현 체크포인트가 진행된 상태**이며, 오프라인/fake 제공자 기반 CLI, PDF 구조 추출, 안전 게이트, ICML desk check, 외부 근거 클라이언트, specialist/synthesis, Markdown 저장 경로가 구현되어 있습니다. Hosted LLM 클라이언트와 실제 운영 품질 보장은 아직 구현 완료로 주장하지 않습니다. 도구는 단일 PDF를 안전하게 읽고, ICML 2026 Main Track의 공식 제출 제한과 리뷰 양식을 기준으로 점검하며, 논문 내부 근거와 외부 메타데이터 출처를 분리해 Markdown 리뷰 초안을 저장합니다.

핵심 목표는 다음과 같습니다.

- PDF에서 제목, 초록, 본문 섹션, 표, 그림, 수식, 참고문헌, 페이지 단위 근거를 추출한다.
- 낮은 품질의 스캔, 손상/암호화 PDF, 프롬프트 인젝션 의심 입력을 안전하게 거절한다.
- ICML 2026 Main Track 제출 제한을 기준으로 단일 PDF, 50MB 이하, 본문 8쪽 제한, 익명성, LaTeX 형식 관련 신호를 점검한다.
- Crossref, Semantic Scholar, arXiv, 공개 OpenReview 근거를 사용하되, 확인되지 않은 사실은 추측하지 않는다.
- 독립 전문 리뷰 관점을 합성해 ICML Main Track의 공식 필드와 점수 범위에 맞춘 Markdown을 만든다.

## 왜 이 도구가 필요한가

리뷰어는 논문 품질, 규정 준수, 인용 정확성, 안전한 LLM 사용 정책을 동시에 확인해야 합니다. 이 도구는 리뷰어의 판단을 대체하지 않고, 반복적인 근거 수집과 형식 검증을 보조합니다. 특히 PDF 본문과 외부 API 응답을 모두 신뢰할 수 없는 입력으로 취급해, 논문 안의 명령문이나 외부 메타데이터 오류가 리뷰 지침을 덮어쓰지 못하게 하는 것이 중요합니다.

## 설치

저장소를 복제하고 Python 3.11+ 가상 환경에 패키지를 설치합니다.

```bash
git clone https://github.com/kwon/who-is-adam.git
cd who-is-adam
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

선택 OCR 지원에는 Python extra와 Tesseract 시스템 패키지가 모두 필요합니다.

```bash
python -m pip install -e '.[ocr]'
```

macOS에서는 Homebrew로 Tesseract를 설치합니다.

```bash
brew install tesseract
```

Debian/Ubuntu Linux에서는 apt로 Tesseract를 설치합니다.

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

설치된 CLI가 보이는지 확인합니다.

```bash
who-is-adam --help
who-is-adam review --help
```

## Agent Skill로 설치

`skills/who-is-adam/SKILL.md`가 기본 실행 표면이며 호스트 에이전트가 PDF를 직접 읽고 리뷰합니다. Claude Code와 Codex에서는 플러그인 설치만으로 사용할 수 있고 Python 패키지는 필요하지 않습니다.

Claude Code:

```text
/plugin marketplace add NomaDamas/who-is-adam
/plugin install who-is-adam
/who-is-adam /path/to/paper.pdf
```

Codex:

```bash
codex plugin marketplace add NomaDamas/who-is-adam
codex plugin add who-is-adam@who-is-adam
```

Codex 호출:

```text
Use $who-is-adam to review /path/to/paper.pdf.
```

Python CLI는 선택적 오프라인 파이프라인 진단 도구입니다. fake LLM 출력과 `unavailable` 외부 근거는 테스트용이며 실제 논문 리뷰로 제시하면 안 됩니다.


## 빠른 시작 CLI

오프라인/fake 제공자 기반 CLI는 구현되어 있으며, 네트워크와 실제 API 키 없이 fake LLM으로 계약 검증용 리뷰 초안을 저장합니다. 외부 제공자 근거는 fixture로 대체하지 않고 `unavailable`로 기록합니다.

```bash
who-is-adam review paper.pdf --output-dir reviews --llm-policy "<assigned policy>" --code-of-conduct-ack --offline
```

인자 의미:

- `paper.pdf`: 로컬 ICML 2026 Main Track 단일 PDF.
- `--output-dir`: 리뷰 Markdown과 진단 파일을 저장할 루트 디렉터리.
- `--llm-policy`: 리뷰어가 배정받은 ICML LLM 사용 정책의 이름 또는 원문. 필수입니다.
- `--code-of-conduct-ack`: ICML 행동 강령 확인을 런타임 메타데이터에 기록했다는 명시적 승인. 필수입니다.
- `--offline`: fake LLM을 사용하고 외부 제공자 근거를 `unavailable`로 기록해 테스트/오프라인 모드로 실행합니다.

## 사용법

현재 구현된 오프라인 경로는 로컬 PDF로 실행합니다. fake LLM은 결정적인 계약 테스트 출력을 만들며, 통합 확인용이지 실제 논문 품질 리뷰가 아닙니다.

```bash
WHO_IS_ADAM_OFFLINE=true who-is-adam review paper.pdf \
  --output-dir reviews \
  --llm-policy "ICML assigned LLM policy checked" \
  --code-of-conduct-ack \
  --offline
```

성공한 실행은 종료 코드 `0`으로 끝나며 다음과 같은 버전 Markdown 파일을 씁니다.

```text
reviews/a_study_of_adam/a_study_of_adam_review_1.md
```

안전한 거절은 종료 코드 `2`로 끝나고 진단을 출력하며 리뷰 Markdown을 쓰지 않습니다. 예를 들어 PDF가 아닌 입력은 리뷰 생성 전에 거절됩니다.

```bash
who-is-adam review notes.txt --output-dir reviews --llm-policy "ICML assigned LLM policy checked" --code-of-conduct-ack --offline
```

필수 런타임 확인값이 없으면 CLI 사용 오류입니다. 예:

```bash
who-is-adam review paper.pdf --output-dir reviews --offline
```

현재 체크포인트에서는 hosted production review가 연결되어 있지 않습니다. 오프라인 fake 리뷰는 구현된 파이프라인의 계약 테스트이며, 운영 품질의 ICML 리뷰라고 설명하면 안 됩니다.
Hosted LLM 제공자 설정은 환경 변수 스키마에 존재하지만, 현재 체크포인트에서는 hosted LLM 클라이언트가 아직 연결되지 않았으므로 운영 리뷰 품질을 보장하는 경로로 문서화하지 않습니다.

## 지원 범위와 제한

지원 범위는 ICML 2026 Main Track PDF 리뷰 보조로 한정됩니다. 공식 확인된 제한은 다음과 같이 문서화합니다.

- 제출물은 단일 PDF여야 하며 최대 50MB입니다.
- 메인 본문은 8쪽까지 허용되고, 참고문헌과 부록은 본문 뒤에 둘 수 있습니다.
- 제출물은 익명화되어야 하며, LaTeX 형식 요구사항과 페이지/형식 위반은 자동 거절 사유가 될 수 있습니다.
- 리뷰어는 배정된 LLM 정책, 비밀유지, 전문적이고 건설적인 태도, 행동 강령 확인을 따라야 합니다.
- 공식 Main Track 리뷰 점수 범위는 Soundness/Presentation/Contribution 1-4, Rating 1-6, Confidence 1-5입니다.

비지원 범위:

- Position Track 리뷰.
- OpenReview 또는 ICML 시스템에 실제 제출.
- 논문 수정, 재작성, 저자 대리 행위.
- 공개 근거가 없는 OpenReview 과거 장단점 생성.
- 모든 스캔 PDF에 대한 OCR 성공 보장.
- 현재 체크포인트에서 hosted LLM 제공자에 의존하는 운영 리뷰 생성.

## 안전한 거절 정책

도구는 리뷰를 생성하기 전에 실패해야 할 입력을 먼저 거절하는 방향으로 설계됩니다. 다음 상황에서는 공식 리뷰 Markdown을 저장하지 않고, 운영자가 이해할 수 있는 진단을 반환해야 합니다.

- PDF가 아니거나, 존재하지 않거나, 50MB를 초과하거나, 손상/암호화되어 구조 추출이 불가능한 경우.
- 텍스트 밀도나 OCR 신뢰도가 낮아 논문 내용을 충분히 읽을 수 없는 경우.
- PDF 본문에 리뷰어/시스템 지시를 무시하라는 명령, 점수 조작 요청, 도구 정책 변경 요구 등 프롬프트 인젝션 신호가 있는 경우.
- LLM 제공자가 JSON schema 제약 출력을 지원하지 않거나, 필수 모델/API 키 설정이 빠졌거나, 검증된 JSON을 반복해서 만들지 못하는 경우.

안전 거절은 논문 품질 평가가 아니라 입력 또는 실행 환경이 신뢰 가능한 리뷰 생성을 허용하지 않는다는 판단입니다.

## 증거 정책

모든 판단은 근거 출처를 구분해야 합니다.

- PDF 내부 근거: 페이지, 섹션, 인용된 텍스트 span을 기록합니다.
- 외부 메타데이터: Crossref, Semantic Scholar, arXiv는 참고문헌 사실 확인 보조로만 사용합니다.
- OpenReview: 공개 OpenReview 근거가 있을 때만 선행 연구의 과거 강점/약점이나 비교 근거로 사용합니다.
- 근거 없음: API 부재, rate limit, 검색 실패, 공개 근거 없음은 `unavailable`로 남기며 추측 문장을 만들지 않습니다.

PDF 본문, 참고문헌, 외부 리뷰 텍스트는 모두 신뢰 경계 밖의 입력입니다. 이 데이터는 리뷰 지침을 바꾸거나 시스템 규칙을 덮어쓸 수 없습니다.

## 출력 위치와 파일 이름

성공한 리뷰는 논문 제목을 정규화한 디렉터리 아래에 버전 번호가 붙은 Markdown으로 저장합니다.

```text
<output-dir>/<normalized_title>/<normalized_title>_review_{n}.md
```

`normalized_title`은 내부 slug/path sanitizer가 만든 파일 시스템 안전 이름입니다. `n`은 같은 디렉터리에 이미 있는 리뷰 번호의 최댓값에 1을 더한 값입니다. 예를 들어 `reviews/a_study_of_adam/a_study_of_adam_review_3.md`가 존재하면 다음 저장 파일은 `a_study_of_adam_review_4.md`가 됩니다. 충돌이 감지되면 원자적 쓰기와 번호 재계산으로 기존 결과를 덮어쓰지 않아야 합니다.

## 환경 변수와 제공자 요약

운영 환경 변수, fake/offline 모드, 제공자별 실패 의미는 [운영자 가이드](operator-guide.md)의 `환경 변수 매트릭스`를 따릅니다. 주요 제공자는 LLM, OpenReview, Semantic Scholar, Crossref, arXiv, 선택적 OCR/Tesseract입니다.

## 개발/검증 체크포인트

단계별 파일 범위, 검증 명령, 기대 동작, 커밋 메시지는 [구현 체크포인트](implementation-checkpoints.md)에 정리되어 있습니다. 현재 프로젝트는 문서 전용 제안 단계를 넘어 오프라인 CLI/리뷰 경로의 제품 코드와 테스트가 존재하는 상태입니다.
