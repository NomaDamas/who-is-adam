#!/usr/bin/env python3
"""Safe wrapper for the installed who-is-adam review CLI."""

from __future__ import annotations

import argparse
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

    command = [
        "who-is-adam",
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

    completed = subprocess.run(command, shell=False, check=False)
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
