from __future__ import annotations

from pathlib import Path


DOC_REQUIREMENTS = {
    "README.md": ["제품 제안 요약", "안전한 거절 정책", "증거 정책", "출력 위치와 파일 이름"],
    "docs/ko/product-proposal.md": ["처리 흐름", "리뷰 품질 원칙", "사람이 최종 판단한다"],
    "docs/ko/operator-guide.md": ["환경 변수 매트릭스", "거절 사례", "오프라인/테스트 모드"],
    "docs/ko/evidence-policy.md": ["신뢰 경계", "OpenReview 근거 제한", "프롬프트 인젝션 처리"],
    "docs/ko/implementation-checkpoints.md": ["Git 커밋 계획", "검증 명령", "커밋 메시지"],
}


def test_required_korean_documentation_headings() -> None:
    root = Path(__file__).resolve().parents[1]

    for relative_path, headings in DOC_REQUIREMENTS.items():
        text = (root / relative_path).read_text(encoding="utf-8")
        missing = [heading for heading in headings if heading not in text]
        assert not missing, f"{relative_path} missing {missing}"
