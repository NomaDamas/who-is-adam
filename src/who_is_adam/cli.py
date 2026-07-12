"""Command-line interface for who-is-adam."""

from __future__ import annotations

from enum import IntEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from who_is_adam.config import ReviewConfig
from who_is_adam.models import ReviewRunStatus
from who_is_adam.review.orchestrator import run_review

app = typer.Typer(help="Evidence-grounded ICML PDF review assistant.")


@app.callback()
def main() -> None:
    """Evidence-grounded ICML PDF review assistant."""
console = Console()
error_console = Console(stderr=True)


class ExitCode(IntEnum):
    SUCCESS = 0
    REFUSED = 2
    CONFIG = 3
    INTERNAL = 4




@app.command()
def review(
    pdf_path: Annotated[Path, typer.Argument(exists=False, dir_okay=False, readable=True)],
    output_dir: Annotated[Path, typer.Option("--output-dir", file_okay=False)] = Path("reviews"),
    llm_policy: Annotated[str, typer.Option("--llm-policy", help="Assigned ICML LLM policy.")] = "",
    code_of_conduct_ack: Annotated[
        bool,
        typer.Option(
            "--code-of-conduct-ack",
            help="Confirm that the ICML reviewer code of conduct was checked.",
        ),
    ] = False,
    offline: Annotated[bool, typer.Option("--offline", help="Force fake/offline providers.")] = False,
) -> None:
    """Review one local ICML Main Track PDF once the orchestrator exists."""

    if not llm_policy.strip():
        error_console.print("[red]Configuration error:[/red] --llm-policy is required.")
        raise typer.Exit(ExitCode.CONFIG)
    if not code_of_conduct_ack:
        error_console.print("[red]Configuration error:[/red] --code-of-conduct-ack is required.")
        raise typer.Exit(ExitCode.CONFIG)

    try:
        config = ReviewConfig.from_env()
        if offline:
            config = config.model_copy(update={"offline": True})
            config = ReviewConfig.model_validate(config.model_dump(mode="python"))
        result = run_review(
            pdf_path=pdf_path,
            output_dir=output_dir,
            llm_policy=llm_policy,
            code_of_conduct_acknowledged=code_of_conduct_ack,
            config=config,
        )
        if result.status is ReviewRunStatus.REFUSED:
            refusal = result.refusal
            reason = refusal.reason if refusal is not None else "review refused"
            error_console.print(f"[yellow]Review refused:[/yellow] {reason}")
            if refusal is not None:
                for diagnostic in refusal.diagnostics:
                    error_console.print(diagnostic.model_dump_json())
            raise typer.Exit(ExitCode.REFUSED)
        if result.output_path is None:
            error_console.print("[red]Internal error:[/red] orchestrator did not return an output path.")
            raise typer.Exit(ExitCode.INTERNAL)
        output_path = result.output_path
    except typer.Exit:
        raise
    except ValueError as exc:
        error_console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(ExitCode.CONFIG) from exc
    except Exception as exc:
        error_console.print(f"[red]Internal error:[/red] {exc}")
        raise typer.Exit(ExitCode.INTERNAL) from exc

    console.print(f"Review saved: {output_path}")
    raise typer.Exit(ExitCode.SUCCESS)


if __name__ == "__main__":
    app()
