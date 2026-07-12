"""Command-line interface for who-is-adam."""

from __future__ import annotations

from enum import IntEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from who_is_adam.config import ReviewConfig

app = typer.Typer(help="Evidence-grounded ICML PDF review assistant.")
console = Console()
error_console = Console(stderr=True)


class ExitCode(IntEnum):
    SUCCESS = 0
    REFUSED = 2
    CONFIG = 3
    INTERNAL = 4


class OrchestratorUnavailableError(RuntimeError):
    """Raised until the review orchestrator checkpoint is implemented."""


def _review_with_orchestrator(
    *,
    pdf_path: Path,
    output_dir: Path,
    llm_policy: str,
    code_of_conduct_acknowledged: bool,
    config: ReviewConfig,
) -> Path:
    del pdf_path, output_dir, llm_policy, code_of_conduct_acknowledged, config
    raise OrchestratorUnavailableError(
        "Review orchestration is not implemented yet; checkpoint 7 will wire PDF extraction, "
        "safety gates, evidence clients, synthesis, and Markdown persistence."
    )


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
        output_path = _review_with_orchestrator(
            pdf_path=pdf_path,
            output_dir=output_dir,
            llm_policy=llm_policy,
            code_of_conduct_acknowledged=code_of_conduct_ack,
            config=config,
        )
    except OrchestratorUnavailableError as exc:
        error_console.print(f"[yellow]Review unavailable:[/yellow] {exc}")
        raise typer.Exit(ExitCode.INTERNAL) from exc
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
