"""CLI entrypoint for research-digest."""

from pathlib import Path
from typing import Annotated

import typer

from research_digest import __version__
from research_digest.config import load_config
from research_digest.logging_config import setup_logging

app = typer.Typer(name="research-digest", help="Local-first research digest generator.")


def _version_callback(value: bool) -> None:
    if value:
        print(f"research-digest {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version and exit."),
    ] = None,
) -> None:
    """Research digest CLI."""


@app.command()
def fetch(
    config: Annotated[Path | None, typer.Option("--config", help="Path to topics config YAML.")] = None,
    since_last_run: Annotated[bool, typer.Option("--since-last-run", help="Fetch since last successful run.")] = False,
    lookback_days: Annotated[int | None, typer.Option("--lookback-days", help="Override lookback days.")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print query without fetching.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Fetch papers from arXiv."""
    setup_logging("DEBUG" if verbose else None)
    cfg = load_config(config)
    typer.echo(f"Config loaded: {cfg.sources.arxiv.categories}")
    typer.echo("fetch: not yet implemented (wired in M2)")


@app.command()
def rank(
    config: Annotated[Path | None, typer.Option("--config", help="Path to topics config YAML.")] = None,
    run_id: Annotated[str | None, typer.Option("--run-id", help="Run ID to rank (default: most recent).")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Score and rank stored papers."""
    setup_logging("DEBUG" if verbose else None)
    cfg = load_config(config)
    typer.echo("rank: not yet implemented (wired in M3)")


@app.command()
def build(
    config: Annotated[Path | None, typer.Option("--config", help="Path to topics config YAML.")] = None,
    run_id: Annotated[str | None, typer.Option("--run-id", help="Run ID to build digest for.")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Build Markdown digest from ranked papers."""
    setup_logging("DEBUG" if verbose else None)
    cfg = load_config(config)
    typer.echo("build: not yet implemented (wired in M3)")


@app.command()
def run(
    config: Annotated[Path | None, typer.Option("--config", help="Path to topics config YAML.")] = None,
    since_last_run: Annotated[bool, typer.Option("--since-last-run", help="Fetch since last successful run.")] = False,
    lookback_days: Annotated[int | None, typer.Option("--lookback-days", help="Override lookback days.")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print query without fetching.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Run full pipeline: fetch, rank, build digest."""
    setup_logging("DEBUG" if verbose else None)
    cfg = load_config(config)
    typer.echo("run: not yet implemented (wired in M3)")
