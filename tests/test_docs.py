from __future__ import annotations
import re

from pathlib import Path


ENGLISH_DOC_REQUIREMENTS = {
    "docs/product-proposal.md": [
        "Processing flow",
        "Review quality principles",
        "Humans make the final judgment",
    ],
    "docs/operator-guide.md": [
        "Environment variable matrix",
        "Refusal examples",
        "Offline/test mode",
    ],
    "docs/evidence-policy.md": [
        "Trust boundary",
        "OpenReview evidence limits",
        "Prompt-injection handling",
    ],
    "docs/implementation-checkpoints.md": [
        "Git commit plan",
        "Verification command",
        "Commit messages",
    ],
    "docs/skill-guide.md": [
        "Purpose and supported workflow",
        "Input/output contract",
        "Pipeline topology",
        "Agent roster",
        "Strict independence and synthesis rules",
        "PDF and prompt-injection refusal gates",
        "Evidence and provenance rules",
        "ICML official output fields and scales",
        "Configuration and offline mode",
        "Installation and CLI help",
        "Install as an Agent Skill",
        "Environment setup",
        "Current offline/fake limitation",
        "How to invoke CLI and Python API",
        "How to extend or add a specialist without breaking contracts",
        "Testing strategy",
        "Failure handling",
        "Worked end-to-end example",
    ],
}

KOREAN_DOC_REQUIREMENTS = {
    "docs/ko/product-proposal.md": ["처리 흐름", "리뷰 품질 원칙", "사람이 최종 판단한다"],
    "docs/ko/operator-guide.md": ["환경 변수 매트릭스", "거절 사례", "오프라인/테스트 모드"],
    "docs/ko/evidence-policy.md": ["신뢰 경계", "OpenReview 근거 제한", "프롬프트 인젝션 처리"],
    "docs/ko/implementation-checkpoints.md": ["Git 커밋 계획", "검증 명령", "커밋 메시지"],
    "docs/ko/skill-guide.md": [
        "목적과 지원 워크플로",
        "입력/출력 계약",
        "파이프라인 토폴로지",
        "에이전트 로스터",
        "엄격한 독립성과 종합 규칙",
        "PDF와 프롬프트 인젝션 거절 게이트",
        "근거와 출처 규칙",
        "ICML 공식 출력 필드와 척도",
        "구성과 오프라인 모드",
        "설치와 CLI 도움말",
        "Agent Skill로 설치",
        "환경 설정",
        "현재 오프라인/fake 제한",
        "CLI와 Python API 호출 방법",
        "계약을 깨지 않고 전문가를 확장하거나 추가하는 방법",
        "테스트 전략",
        "실패 처리",
        "전체 흐름 예시",
    ],
}

DOC_TRANSLATION_PAIRS = {
    "docs/product-proposal.md": "docs/ko/product-proposal.md",
    "docs/operator-guide.md": "docs/ko/operator-guide.md",
    "docs/evidence-policy.md": "docs/ko/evidence-policy.md",
    "docs/implementation-checkpoints.md": "docs/ko/implementation-checkpoints.md",
    "docs/skill-guide.md": "docs/ko/skill-guide.md",
}

KOREAN_PHRASES = {
    phrase for phrases in KOREAN_DOC_REQUIREMENTS.values() for phrase in phrases
}
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)#][^)]*)\)")
DOCS_WITH_OFFLINE_PROVIDER_SEMANTICS = [
    "README.md",
    "docs/product-proposal.md",
    "docs/operator-guide.md",
    "docs/ko/README.md",
    "docs/ko/product-proposal.md",
    "docs/ko/operator-guide.md",
    "docs/skill-guide.md",
    "docs/ko/skill-guide.md",
]

STALE_FIXTURE_BACKED_OFFLINE_PATTERNS = [
    re.compile(r"supports deterministic offline runs with a fake LLM and fixture-backed providers", re.IGNORECASE),
    re.compile(r"--offline`:[^\n]*fake LLM[^\n]*fixture 기반 제공자"),
]

STALE_ASSIGNMENT_PROCESS_PATTERNS = [
    re.compile(r"사용자 지시에 따라[^\n.]*테스트[^\n.]*포매터[^\n.]*Git 명령을 실행하지 않습니다"),
    re.compile(r"do not run tests[^\n.]*formatters[^\n.]*Git", re.IGNORECASE),
]


CONTRACT_PARITY_REQUIREMENTS = {
    ("docs/product-proposal.md", "docs/ko/product-proposal.md"): [
        (
            [
                "offline review generation with a fake LLM",
                "external evidence is recorded as `unavailable`",
                "runtime offline mode does not use fixture-backed external providers",
            ],
            [
                "fake LLM을 사용하는 오프라인 리뷰 생성",
                "외부 근거는 결정적 검증을 위해 `unavailable`로 기록",
                "런타임 오프라인 모드는 fixture 기반 외부 제공자를 사용하지 않습니다",
            ],
        ),
    ],
    ("docs/operator-guide.md", "docs/ko/operator-guide.md"): [
        (
            ["WHO_IS_ADAM_LLM_PROVIDER", "WHO_IS_ADAM_OFFLINE", "fake"],
            ["WHO_IS_ADAM_LLM_PROVIDER", "WHO_IS_ADAM_OFFLINE", "fake"],
        ),
        (["prompt-injection", "exit code `2`"], ["프롬프트 인젝션", "`2`: 안전"]),
    ],
    ("docs/evidence-policy.md", "docs/ko/evidence-policy.md"): [
        (
            ["PDF-internal evidence", "External metadata", "OpenReview", "unavailable"],
            ["PDF 내부 근거", "외부 메타데이터 근거", "OpenReview 근거 제한", "unavailable"],
        ),
        (["untrusted", "may not change"], ["비신뢰 입력", "덮어쓰려는 시도"]),
    ],
    ("docs/skill-guide.md", "docs/ko/skill-guide.md"): [
        (
            ["independently", "synthesis", "official ICML review fields"],
            ["독립", "종합", "ICML 공식 출력 필드"],
        ),
        (["Offline mode", "fake LLM", "pytest"], ["오프라인 모드", "fake", "pytest"]),
    ],
}

INSTALL_USAGE_REQUIREMENTS = [
    (
        "docs/skill-guide.md",
        "docs/ko/skill-guide.md",
        [
            "Installation and CLI help",
            "Environment setup",
            "Current offline/fake limitation",
            "ReviewConfig.model_validate",
            "run_review(",
            "`0`: review Markdown was saved",
            "`2`: safe refusal",
            "Desk-check refusal",
            "not real paper-quality reviews",
            "hosted production review generation",
        ],
        [
            "설치와 CLI 도움말",
            "환경 설정",
            "현재 오프라인/fake 제한",
            "ReviewConfig.model_validate",
            "run_review(",
            "`0`: 리뷰 Markdown이 저장",
            "`2`: 리뷰 Markdown을 쓰기 전 안전한 거절",
            "Desk-check refusal",
            "실제 논문 품질 리뷰",
            "hosted production review",
        ],
    ),
]


def _resolve_doc_links(root: Path, relative_path: str) -> set[str]:
    text = (root / relative_path).read_text(encoding="utf-8")
    parent = Path(relative_path).parent
    resolved: set[str] = set()
    for target in LINK_PATTERN.findall(text):
        if ":" in target or target.startswith("#"):
            continue
        target_path = (parent / target).resolve().relative_to(root.resolve()).as_posix()
        resolved.add(target_path)
    return resolved


def _expected_relative_link(source_path: str, target_path: str) -> str:
    source_parent = Path(source_path).parent
    return (
        target_path
        if source_parent == Path(".")
        else Path(target_path).relative_to(source_parent).as_posix()
    )


def _read(root: Path, relative_path: str) -> str:
    return (root / relative_path).read_text(encoding="utf-8")




def test_required_english_default_documentation_headings() -> None:
    root = Path(__file__).resolve().parents[1]

    for relative_path, headings in ENGLISH_DOC_REQUIREMENTS.items():
        text = (root / relative_path).read_text(encoding="utf-8")
        missing = [heading for heading in headings if heading not in text]
        assert not missing, f"{relative_path} missing {missing}"


def test_required_korean_translation_documentation_headings() -> None:
    root = Path(__file__).resolve().parents[1]

    for relative_path, headings in KOREAN_DOC_REQUIREMENTS.items():
        text = (root / relative_path).read_text(encoding="utf-8")
        missing = [heading for heading in headings if heading not in text]
        assert not missing, f"{relative_path} missing {missing}"


def test_english_default_docs_link_to_korean_translations() -> None:
    root = Path(__file__).resolve().parents[1]

    for english_path, korean_path in DOC_TRANSLATION_PAIRS.items():
        english_text = (root / english_path).read_text(encoding="utf-8")
        english_to_korean = _expected_relative_link(english_path, korean_path)

        assert english_to_korean in english_text, f"{english_path} must link to {korean_path}"


def test_translation_pairs_are_complete_and_reciprocal() -> None:
    root = Path(__file__).resolve().parents[1]

    assert set(DOC_TRANSLATION_PAIRS) == set(ENGLISH_DOC_REQUIREMENTS)
    assert set(DOC_TRANSLATION_PAIRS.values()) == set(KOREAN_DOC_REQUIREMENTS)

    for english_path, korean_path in DOC_TRANSLATION_PAIRS.items():
        english_links = _resolve_doc_links(root, english_path)
        korean_links = _resolve_doc_links(root, korean_path)

        assert korean_path in english_links, f"{english_path} must resolve-link to {korean_path}"
        assert english_path in korean_links, f"{korean_path} must resolve-link back to {english_path}"


def test_key_contract_and_status_parity_between_english_and_korean_docs() -> None:
    root = Path(__file__).resolve().parents[1]

    for (english_path, korean_path), parity_checks in CONTRACT_PARITY_REQUIREMENTS.items():
        english_text = _read(root, english_path)
        korean_text = _read(root, korean_path)
        for english_needles, korean_needles in parity_checks:
            missing_english = [needle for needle in english_needles if needle not in english_text]
            missing_korean = [needle for needle in korean_needles if needle not in korean_text]
            assert not missing_english, f"{english_path} missing contract/status terms {missing_english}"
            assert not missing_korean, f"{korean_path} missing contract/status terms {missing_korean}"


def test_offline_runtime_semantics_do_not_claim_fixture_backed_external_providers() -> None:
    root = Path(__file__).resolve().parents[1]

    for relative_path in DOCS_WITH_OFFLINE_PROVIDER_SEMANTICS:
        text = _read(root, relative_path)
        stale_matches = [
            pattern.pattern for pattern in STALE_FIXTURE_BACKED_OFFLINE_PATTERNS if pattern.search(text)
        ]
        assert not stale_matches, f"{relative_path} has stale offline provider semantics {stale_matches}"

        if "offline" in text or "오프라인" in text:
            assert "fake" in text, f"{relative_path} should document fake LLM offline behavior"
            assert "unavailable" in text, f"{relative_path} should document unavailable external evidence"


def test_korean_readme_navigation_and_status_stay_current() -> None:
    root = Path(__file__).resolve().parents[1]
    text = _read(root, "docs/ko/README.md")
    links = _resolve_doc_links(root, "docs/ko/README.md")

    for target in [
        "README.md",
        "docs/product-proposal.md",
        "docs/operator-guide.md",
        "docs/evidence-policy.md",
        "docs/implementation-checkpoints.md",
        "docs/skill-guide.md",
        "docs/ko/skill-guide.md",
    ]:
        assert target in links, f"docs/ko/README.md must link to {target}"

    stale_process = [pattern.pattern for pattern in STALE_ASSIGNMENT_PROCESS_PATTERNS if pattern.search(text)]
    assert not stale_process, f"docs/ko/README.md has stale assignment-process text {stale_process}"
    assert "제품 코드와 테스트가 존재" in text
    assert "fixture로 대체하지 않고 `unavailable`" in text


def test_root_readme_does_not_depend_on_korean_required_phrases() -> None:
    root = Path(__file__).resolve().parents[1]
    readme_text = (root / "README.md").read_text(encoding="utf-8")
    leaked_phrases = [phrase for phrase in KOREAN_PHRASES if phrase in readme_text]

    assert not leaked_phrases, f"README.md should use English headings, found {leaked_phrases}"

def test_installation_and_usage_guidance_stays_durable_and_translated() -> None:
    root = Path(__file__).resolve().parents[1]

    for english_path, korean_path, english_needles, korean_needles in INSTALL_USAGE_REQUIREMENTS:
        english_text = _read(root, english_path)
        korean_text = _read(root, korean_path)

        missing_english = [needle for needle in english_needles if needle not in english_text]
        missing_korean = [needle for needle in korean_needles if needle not in korean_text]

        assert not missing_english, f"{english_path} missing install/use guidance {missing_english}"
        assert not missing_korean, f"{korean_path} missing install/use translation {missing_korean}"


def test_agent_skill_package_installation_docs_cover_runtime_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    skill_path = root / "skills/who-is-adam/SKILL.md"

    assert skill_path.is_file(), "custom skill package must ship skills/who-is-adam/SKILL.md"

    skill_text = skill_path.read_text(encoding="utf-8")
    assert skill_text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    frontmatter = skill_text.split("---", 2)[1]
    for key in ["name:", "description:"]:
        assert key in frontmatter, f"SKILL.md frontmatter missing {key}"

    docs = {
        "README.md": _read(root, "README.md"),
        "docs/skill-guide.md": _read(root, "docs/skill-guide.md"),
        "docs/ko/README.md": _read(root, "docs/ko/README.md"),
        "docs/ko/skill-guide.md": _read(root, "docs/ko/skill-guide.md"),
    }
    shared_needles = [
        "skills/who-is-adam/",
        "skills/who-is-adam/SKILL.md",
        ".gjc/skills/",
        "~/.gjc/skills/",
        ".claude/skills/",
        "~/.claude/skills/",
        "cp -R skills/who-is-adam",
        "python -m pip install -e .",
        "/skill:who-is-adam /path/to/paper.pdf",
        "who-is-adam review",
        "SKILL.md",
        "CLI",
        "unavailable",
    ]

    for relative_path, text in docs.items():
        missing = [needle for needle in shared_needles if needle not in text]
        assert not missing, f"{relative_path} missing Agent Skill installation details {missing}"
        assert "default GJC workflow" in text or "기본 GJC workflow" in text
        assert "natural-language" in text or "자연어 트리거" in text
