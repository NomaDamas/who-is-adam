from __future__ import annotations

import json
from pathlib import Path


def _read(root: Path, relative_path: str) -> str:
    return (root / relative_path).read_text(encoding="utf-8")


def test_agent_skill_package_exposes_plugin_first_runtime() -> None:
    root = Path(__file__).resolve().parents[1]
    skill_path = root / "skills/who-is-adam/SKILL.md"

    assert skill_path.is_file(), "custom skill package must ship skills/who-is-adam/SKILL.md"

    skill_text = skill_path.read_text(encoding="utf-8")
    assert skill_text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    frontmatter = skill_text.split("---", 2)[1]
    for key in ["name:", "description:"]:
        assert key in frontmatter, f"SKILL.md frontmatter missing {key}"

    required_files = [
        ".agents/plugins/marketplace.json",
        ".claude-plugin/marketplace.json",
        ".claude-plugin/plugin.json",
        ".codex-plugin/plugin.json",
        "skills/who-is-adam/agents/openai.yaml",
    ]
    for relative_path in required_files:
        assert (root / relative_path).is_file(), f"plugin package missing {relative_path}"

    claude_marketplace = json.loads(_read(root, ".claude-plugin/marketplace.json"))
    assert claude_marketplace["plugins"][0]["skills"] == ["./skills/who-is-adam"]

    codex_manifest = json.loads(_read(root, ".codex-plugin/plugin.json"))
    assert codex_manifest["skills"] == "./skills/"

    readme_text = _read(root, "README.md")
    install_needles = [
        "/plugin marketplace add NomaDamas/who-is-adam",
        "/plugin install who-is-adam",
        "/who-is-adam /path/to/paper.pdf",
        "codex plugin marketplace add NomaDamas/who-is-adam",
        "codex plugin add who-is-adam@who-is-adam",
        "Use $who-is-adam to review /path/to/paper.pdf.",
        "Python is not required",
        "optional deterministic/offline contract checks",
    ]
    missing = [needle for needle in install_needles if needle not in readme_text]
    assert not missing, f"README.md missing plugin-first install details {missing}"

    assert "primary runtime" in skill_text
    assert "Python CLI is optional" in skill_text
    assert "never assume the current workspace contains this repository" in skill_text


def test_skill_contract_requires_official_review_shape() -> None:
    root = Path(__file__).resolve().parents[1]
    skill_text = _read(root, "skills/who-is-adam/SKILL.md")

    required_sections = [
        "## Desk Review",
        "## Summary",
        "## Strengths",
        "## Weaknesses",
        "## Questions for Authors",
        "## Soundness",
        "## Presentation",
        "## Contribution",
        "## Rating",
        "## Confidence",
        "## Evidence and Provenance",
        "## Reviewer Lens Notes",
        "### Field/significance",
        "### Methodology",
        "### Domain/prior work",
        "### Logic/counterargument",
        "### Reproducibility/experiments",
        "## Adversarial Deliberation",
        "## Limitations",
    ]
    missing = [section for section in required_sections if section not in skill_text]
    assert not missing, f"SKILL.md missing required review sections {missing}"

    for score_format in ["Score: N/4", "Score: N/6", "Score: N/5"]:
        assert score_format in skill_text, f"SKILL.md missing score format {score_format}"
    assert "Quick mode uses the same section order and score scales" in skill_text
