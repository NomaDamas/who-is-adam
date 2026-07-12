#!/usr/bin/env python3
"""Safe wrapper for the installed who-is-adam review CLI."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the installed who-is-adam review CLI with the required safety flags."
    )
    parser.add_argument(
        "--pdf-path",
        required=True,
        type=Path,
        help="Path to the local PDF to review.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory where who-is-adam writes review artifacts.",
    )
    parser.add_argument(
        "--llm-policy",
        required=True,
        help="Assigned reviewer LLM-use policy label or text.",
    )
    parser.add_argument(
        "--code-of-conduct-ack",
        required=True,
        action="store_true",
        help="Required acknowledgement that the reviewer code of conduct was checked.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use the installed CLI's deterministic fake/offline mode for contract testing only.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plugin_root = Path(__file__).resolve().parents[3]
    cli_path = plugin_root / "src/who_is_adam/cli.py"
    if not cli_path.is_file():
        print(f"Bundled who-is-adam CLI source is unavailable: {cli_path}", file=sys.stderr)
        return 127

    env = os.environ.copy()
    source_path = str(plugin_root / "src")
    existing_python_path = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{source_path}{os.pathsep}{existing_python_path}" if existing_python_path else source_path
    )

    command = [
        sys.executable,
        str(cli_path),
        "review",
        str(args.pdf_path),
        "--output-dir",
        str(args.output_dir),
        "--llm-policy",
        args.llm_policy,
        "--code-of-conduct-ack",
    ]
    if args.offline:
        command.append("--offline")

    completed = subprocess.run(command, shell=False, check=False, env=env)
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
