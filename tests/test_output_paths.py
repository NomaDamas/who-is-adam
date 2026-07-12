from __future__ import annotations

import pytest

from who_is_adam.output.paths import OutputPathError, collision_safe_path, persist_markdown_atomic


def test_collision_safe_path_uses_versioned_max_plus_one(tmp_path) -> None:
    folder = tmp_path / "paper"
    folder.mkdir()
    base = folder / "paper_review_1.md"
    base.write_text("v1", encoding="utf-8")
    (folder / "paper_review_3.md").write_text("v3", encoding="utf-8")
    (folder / "paper-review-99.md").write_text("ignored legacy name", encoding="utf-8")

    assert collision_safe_path(base) == folder / "paper_review_4.md"


def test_persist_markdown_atomic_writes_complete_versioned_file(tmp_path) -> None:
    folder = tmp_path / "test-paper"
    folder.mkdir()
    (folder / "test-paper_review_1.md").write_text("original", encoding="utf-8")

    output = persist_markdown_atomic("## Summary\n\nDeterministic review.\n", tmp_path, "Test Paper")

    assert output == folder / "test-paper_review_2.md"
    assert output.read_text(encoding="utf-8") == "## Summary\n\nDeterministic review.\n"
    assert (folder / "test-paper_review_1.md").read_text(encoding="utf-8") == "original"
    assert not list(folder.glob("*.tmp"))


def test_persist_markdown_atomic_rejects_symlinked_paper_folder(tmp_path) -> None:
    output_dir = tmp_path / "reviews"
    outside_dir = tmp_path / "outside"
    output_dir.mkdir()
    outside_dir.mkdir()
    (output_dir / "test-paper").symlink_to(outside_dir, target_is_directory=True)

    with pytest.raises(OutputPathError, match="symlink"):
        persist_markdown_atomic("review", output_dir, "Test Paper")

    assert not list(outside_dir.iterdir())
