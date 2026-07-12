"""Safe output paths and atomic Markdown persistence."""

from __future__ import annotations

import os
import re
from pathlib import Path

MAX_SLUG_LENGTH = 96
_COLLAPSE_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
_COLLAPSE_DOTS = re.compile(r"[.]{2,}")


class OutputPathError(RuntimeError):
    """Raised when a safe output path cannot be created."""


def safe_slug(value: str, *, fallback: str = "review") -> str:
    """Return a lowercase deterministic slug safe for a single path component."""
    candidate = _COLLAPSE_UNSAFE.sub("-", value.strip().casefold())
    candidate = _COLLAPSE_DOTS.sub(".", candidate)
    candidate = candidate.strip(" ._-")
    if not candidate:
        candidate = fallback
    if candidate in {".", ".."} or "/" in candidate or "\\" in candidate:
        raise OutputPathError(f"unsafe slug component: {value!r}")
    return candidate[:MAX_SLUG_LENGTH].rstrip(" ._-") or fallback


def markdown_output_path(output_dir: Path, title: str, *, suffix: str = ".md") -> Path:
    """Return the first versioned Markdown path for a title."""
    if suffix != ".md":
        raise OutputPathError("Markdown output suffix must be .md")
    slug = safe_slug(title)
    return output_dir / slug / f"{slug}_review_1{suffix}"


def collision_safe_path(base_path: Path, *, max_collisions: int = 1000) -> Path:
    """Return the max existing review version + 1 for base_path's paper folder."""
    if max_collisions < 0:
        raise ValueError("max_collisions must be non-negative")
    _validate_markdown_path(base_path)
    slug = base_path.parent.name
    pattern = re.compile(rf"^{re.escape(slug)}_review_(\d+)\.md$")
    max_version = 0
    if base_path.parent.exists():
        for path in base_path.parent.iterdir():
            if not path.is_file():
                continue
            match = pattern.fullmatch(path.name)
            if match:
                max_version = max(max_version, int(match.group(1)))
    next_version = max_version + 1
    if next_version > max_collisions + 1:
        raise OutputPathError(f"no collision-free output path after {max_collisions + 1} attempts")
    return base_path.with_name(f"{slug}_review_{next_version}{base_path.suffix}")


def persist_markdown_atomic(markdown: str, output_dir: Path, title: str) -> Path:
    """Persist Markdown with lowercase per-paper folder and exclusive versioned naming."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_dir.is_symlink():
        raise OutputPathError(f"output directory must not be a symlink: {output_dir}")
    if not output_dir.is_dir():
        raise OutputPathError(f"output directory is not a directory: {output_dir}")
    base_path = markdown_output_path(output_dir, title)
    if base_path.parent.is_symlink():
        raise OutputPathError(f"paper output directory must not be a symlink: {base_path.parent}")
    base_path.parent.mkdir(parents=True, exist_ok=True)
    if base_path.parent.is_symlink():
        raise OutputPathError(f"paper output directory must not be a symlink: {base_path.parent}")

    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        directory_fd = os.open(base_path.parent, directory_flags)
    except OSError as exc:
        raise OutputPathError(f"failed to open paper output directory safely: {exc}") from exc

    try:
        for _ in range(1001):
            target = collision_safe_path(base_path)
            _validate_markdown_path(target)
            try:
                fd = os.open(
                    target.name,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o644,
                    dir_fd=directory_fd,
                )
            except FileExistsError:
                continue
            except OSError as exc:
                raise OutputPathError(f"failed to persist Markdown atomically: {exc}") from exc
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(markdown)
                    handle.flush()
                    os.fsync(handle.fileno())
                return target
            except OSError as exc:
                try:
                    os.unlink(target.name, dir_fd=directory_fd)
                except OSError:
                    pass
                raise OutputPathError(f"failed to persist Markdown atomically: {exc}") from exc
        raise OutputPathError("no collision-free output path after 1001 attempts")
    finally:
        os.close(directory_fd)


def _validate_markdown_path(path: Path) -> None:
    if path.suffix != ".md":
        raise OutputPathError(f"unsafe Markdown output path: {path}")
    slug = path.parent.name
    if slug != safe_slug(slug):
        raise OutputPathError(f"unsafe Markdown output path: {path}")
    if not re.fullmatch(rf"{re.escape(slug)}_review_\d+\.md", path.name):
        raise OutputPathError(f"unsafe Markdown output path: {path}")
