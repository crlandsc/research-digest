"""CLI entrypoint for research-digest."""

from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer

from research_digest import __version__
from research_digest.config import load_config
from research_digest.logging_config import setup_logging
from research_digest.storage.db import get_connection
from research_digest.storage.repository import PaperRepository

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
    from research_digest.fetchers.arxiv import build_query, compute_date_range
    from research_digest.pipeline.fetch import run_fetch

    setup_logging("DEBUG" if verbose else None)
    cfg = load_config(config)

    if dry_run:
        arxiv_cfg = cfg.sources.arxiv
        lb = lookback_days or arxiv_cfg.lookback_days
        start, end = compute_date_range(lb)
        query = build_query(arxiv_cfg, start, end)
        typer.echo(f"Config: {arxiv_cfg.categories} + {arxiv_cfg.keyword_queries}")
        typer.echo(f"Query: {query}")
        typer.echo(f"Date range: {start.isoformat()} to {end.isoformat()}")
        return

    conn = get_connection()
    repo = PaperRepository(conn)
    rid = str(uuid4())
    repo.create_run(rid)

    try:
        total, new = run_fetch(cfg, repo, rid, since_last_run, lookback_days)
        repo.complete_run(rid, status="completed", papers_fetched=total, papers_new=new)
        typer.echo(f"Fetched {total} papers ({new} new) [run: {rid[:8]}]")
    except Exception as e:
        repo.complete_run(rid, status="failed")
        typer.echo(f"Fetch failed: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def rank(
    config: Annotated[Path | None, typer.Option("--config", help="Path to topics config YAML.")] = None,
    run_id: Annotated[str | None, typer.Option("--run-id", help="Run ID to rank (default: most recent).")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Score and rank stored papers."""
    from research_digest.pipeline.rank import run_rank

    setup_logging("DEBUG" if verbose else None)
    cfg = load_config(config)

    conn = get_connection()
    repo = PaperRepository(conn)

    if run_id is None:
        last = repo.get_most_recent_run()
        if not last:
            typer.echo("No runs found. Run 'research-digest fetch' first.", err=True)
            raise typer.Exit(1)
        run_id = last.run_id

    scored = run_rank(cfg, repo, run_id)
    typer.echo(f"Ranked {len(scored)} papers [run: {run_id[:8]}]")
    for sp in scored[:5]:
        typer.echo(f"  #{sp.rank} ({sp.score:.1f}) {sp.paper.title[:60]}")


@app.command()
def build(
    config: Annotated[Path | None, typer.Option("--config", help="Path to topics config YAML.")] = None,
    run_id: Annotated[str | None, typer.Option("--run-id", help="Run ID to build digest for.")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Build Markdown digest from ranked papers."""
    from research_digest.pipeline.build_digest import run_build

    setup_logging("DEBUG" if verbose else None)
    cfg = load_config(config)

    conn = get_connection()
    repo = PaperRepository(conn)

    if run_id is None:
        last = repo.get_most_recent_run()
        if not last:
            typer.echo("No runs found. Run 'research-digest fetch' first.", err=True)
            raise typer.Exit(1)
        run_id = last.run_id

    path = run_build(cfg, repo, run_id)
    if path:
        typer.echo(f"Digest written to {path}")


@app.command()
def run(
    config: Annotated[Path | None, typer.Option("--config", help="Path to topics config YAML.")] = None,
    since_last_run: Annotated[bool, typer.Option("--since-last-run", help="Fetch since last successful run.")] = False,
    lookback_days: Annotated[int | None, typer.Option("--lookback-days", help="Override lookback days.")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print query without fetching.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Run full pipeline: fetch, rank, build digest."""
    from research_digest.pipeline import run_pipeline

    setup_logging("DEBUG" if verbose else None)
    cfg = load_config(config)

    try:
        path = run_pipeline(cfg, since_last_run, lookback_days, dry_run)
        if path:
            typer.echo(f"Digest written to {path}")
        elif dry_run:
            typer.echo("Dry run complete.")
    except Exception as e:
        typer.echo(f"Pipeline failed: {e}", err=True)
        raise typer.Exit(1)
