from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_skill_wrapper_does_not_execute_ambient_path_binary(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    marker = tmp_path / "ambient-path-binary-ran"
    executable = fake_bin / "who-is-adam"
    executable.write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 23\n", encoding="utf-8")
    executable.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    completed = subprocess.run(
        [
            sys.executable,
            str(root / "skills/who-is-adam/scripts/run_review.py"),
            "--pdf-path",
            str(root / "tests/fixtures/pdfs/valid_icml_text.pdf"),
            "--output-dir",
            str(tmp_path / "reviews"),
            "--llm-policy",
            "test policy",
            "--code-of-conduct-ack",
            "--offline",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr
    assert not marker.exists()
    assert list((tmp_path / "reviews").glob("**/*.md"))
