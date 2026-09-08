"""Command line interface. Phase 1 needs two verbs: `run` and `show`.

    dv run DOC [DOC ...] --version v2.3
    dv run --resume run_abc123 --from judge
    dv show run_abc123
    dv show run_abc123 --verdict incorrect
    dv serve

Keep it to what is needed. Every extra verb is a surface someone has to keep
working while the pipeline underneath is still changing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    name="dv",
    help="Verify documentation claims against source code.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def run(
    docs: Annotated[list[Path] | None, typer.Argument(help="Documents to verify.")] = None,
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("config/default.yaml"),
    version: Annotated[
        str | None,
        typer.Option("--version", help="Product version these documents describe."),
    ] = None,
    resume: Annotated[str | None, typer.Option("--resume", help="Run id to resume.")] = None,
    from_stage: Annotated[
        str | None,
        typer.Option(
            "--from",
            help="With --resume, re-run from this stage using stored earlier outputs. "
            "One of: classify, investigate, evidence, judge.",
        ),
    ] = None,
    fake: Annotated[
        bool,
        typer.Option("--fake", help="Use the fake LLM and fake code tools. No network."),
    ] = False,
) -> None:
    """Start a run, or resume one.

    Prints the run id first, before any work, so a long run can be inspected
    or resumed from another terminal while it is still going.
    """
    raise NotImplementedError


@app.command()
def show(
    run_id: Annotated[str, typer.Argument(help="Run id.")],
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("config/default.yaml"),
    verdict: Annotated[
        str | None,
        typer.Option("--verdict", help="Filter: correct, incorrect, unverifiable."),
    ] = None,
    doc: Annotated[str | None, typer.Option("--doc", help="Filter to one document.")] = None,
    limit: Annotated[int, typer.Option("--limit")] = 50,
) -> None:
    """Show a run's coverage and claims.

    The summary must print BOTH coverage numbers, always:

        extraction coverage   how much of the document was considered checkable
        resolution coverage   how much of that actually reached a verdict

    A run reporting 100% correct at 30% extraction coverage has verified
    almost nothing, and a summary that shows only the verdict counts hides
    exactly that. Print the failed and skipped counts too.
    """
    raise NotImplementedError


@app.command()
def serve(
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("config/default.yaml"),
) -> None:
    """Run the dashboard and API."""
    raise NotImplementedError


if __name__ == "__main__":
    app()
