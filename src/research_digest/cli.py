"""CLI entrypoint for research-digest."""

import logging
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
from dotenv import load_dotenv

load_dotenv()  # Load .env file if present

from research_digest import __version__
from research_digest.config import AppConfig, load_config
from research_digest.logging_config import setup_logging
from research_digest.storage.db import get_connection
from research_digest.storage.repository import PaperRepository

app = typer.Typer(
    name="research-digest",
    help="Local-first research digest generator.",
    no_args_is_help=True,
)


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

    setup_logging("DEBUG" if verbose else "WARNING")
    cfg = load_config(config)

    if dry_run:
        arxiv_cfg = cfg.sources.arxiv
        lb = lookback_days or arxiv_cfg.lookback_days
        start, end = compute_date_range(lb)
        query = build_query(arxiv_cfg, start, end)
        typer.echo(f"Categories: {', '.join(arxiv_cfg.categories)}")
        typer.echo(f"Keywords:   {len(arxiv_cfg.keyword_queries)} configured")
        typer.echo(f"Date range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
        typer.echo(f"Query:      {query}")
        return

    conn = get_connection()
    repo = PaperRepository(conn)
    rid = str(uuid4())
    repo.create_run(rid)

    try:
        total, new = run_fetch(cfg, repo, rid, since_last_run, lookback_days)
        repo.complete_run(rid, status="completed", papers_fetched=total, papers_new=new)
        typer.echo(f"Fetched {total} papers ({new} new)")
    except Exception as e:
        repo.complete_run(rid, status="failed")
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def rank(
    config: Annotated[Path | None, typer.Option("--config", help="Path to topics config YAML.")] = None,
    run_id: Annotated[str | None, typer.Option("--run-id", help="Run ID to rank (default: most recent).")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Score and rank stored papers."""
    from research_digest.pipeline.rank import run_rank

    setup_logging("DEBUG" if verbose else "WARNING")
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
    typer.echo(f"Ranked {len(scored)} papers")
    for sp in scored[:5]:
        typer.echo(f"  #{sp.rank} ({sp.score:.0f}) {sp.paper.title[:70]}")
    if len(scored) > 5:
        typer.echo(f"  ... and {len(scored) - 5} more")


@app.command()
def build(
    config: Annotated[Path | None, typer.Option("--config", help="Path to topics config YAML.")] = None,
    run_id: Annotated[str | None, typer.Option("--run-id", help="Run ID to build digest for.")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Build Markdown digest from ranked papers."""
    from research_digest.pipeline.build_digest import run_build

    setup_logging("DEBUG" if verbose else "WARNING")
    cfg = load_config(config)

    conn = get_connection()
    repo = PaperRepository(conn)

    if run_id is None:
        last = repo.get_most_recent_run()
        if not last:
            typer.echo("No runs found. Run 'research-digest fetch' first.", err=True)
            raise typer.Exit(1)
        run_id = last.run_id

    path, _entries = run_build(cfg, repo, run_id)
    if path:
        typer.echo(f"Digest written to {path}")
    else:
        typer.echo("No papers to include in digest.")


@app.command()
def run(
    config: Annotated[Path | None, typer.Option("--config", help="Path to topics config YAML.")] = None,
    since_last_run: Annotated[bool, typer.Option("--since-last-run", help="Fetch since last successful run.")] = False,
    lookback_days: Annotated[int | None, typer.Option("--lookback-days", help="Override lookback days.")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print query without fetching.")] = False,
    send_email: Annotated[bool, typer.Option("--send-email", help="Send digest via email after build.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Run full pipeline: fetch, rank, build digest."""
    from research_digest.pipeline import run_pipeline

    setup_logging("DEBUG" if verbose else "WARNING")
    cfg = load_config(config)

    try:
        path, entries = run_pipeline(cfg, since_last_run, lookback_days, dry_run)
        if path:
            typer.echo(f"Digest written to {path}")
            if send_email:
                _send_digest_from_entries(cfg, path, entries)
        elif dry_run:
            typer.echo("Dry run complete.")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def send(
    config: Annotated[Path | None, typer.Option("--config", help="Path to topics config YAML.")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Send the most recent digest via email."""
    setup_logging("DEBUG" if verbose else "WARNING")
    cfg = load_config(config)
    _send_digest_standalone(cfg)


def _send_digest_from_entries(cfg: AppConfig, digest_path: Path, entries: list) -> None:
    """Send email using already-built entries (no re-calling LLM)."""
    from research_digest.delivery.gmail import GmailProvider
    from research_digest.rendering.html_email import render_email

    html, text = render_email(entries, cfg)
    provider = GmailProvider()
    subject = f"{cfg.digest.title} — {digest_path.parent.name}"
    provider.send(subject, html, text)
    typer.echo(f"Email sent to {provider.to_addr}")


def _send_digest_standalone(cfg: AppConfig) -> None:
    """Send email for most recent run (loads from DB, uses extractive summaries)."""
    from research_digest.delivery.gmail import GmailProvider
    from research_digest.models import DigestEntry
    from research_digest.pipeline.rank import _determine_topic_group
    from research_digest.pipeline.summarize import extractive_summary
    from research_digest.rendering.html_email import render_email

    conn = get_connection()
    repo = PaperRepository(conn)
    last = repo.get_last_successful_run()
    if not last:
        typer.echo("No successful run found.", err=True)
        raise typer.Exit(1)

    scored = repo.get_top_scored(last.run_id, cfg.ranking.max_candidates_for_digest)
    entries = [
        DigestEntry(
            paper=sp.paper, score=sp.score, rank=sp.rank, reason=sp.reason,
            abstract_excerpt=extractive_summary(sp.paper.abstract),
            topic_group=_determine_topic_group(sp.paper, cfg),
        )
        for sp in scored
    ]

    html, text = render_email(entries, cfg)
    provider = GmailProvider()
    subject = f"{cfg.digest.title} — {last.digest_path.split('/')[-2] if last.digest_path else 'digest'}"
    provider.send(subject, html, text)
    typer.echo(f"Email sent to {provider.to_addr}")


@app.command()
def status(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output.")] = False,
) -> None:
    """Show database and run status."""
    setup_logging("DEBUG" if verbose else "WARNING")

    conn = get_connection()
    repo = PaperRepository(conn)

    paper_count = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    run_count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    completed = conn.execute("SELECT COUNT(*) FROM runs WHERE status='completed'").fetchone()[0]

    typer.echo(f"Papers in database: {paper_count}")
    typer.echo(f"Total runs: {run_count} ({completed} completed)")

    last = repo.get_last_successful_run()
    if last:
        typer.echo(f"Last successful run: {last.completed_at.strftime('%Y-%m-%d %H:%M') if last.completed_at else 'unknown'}")
        typer.echo(f"  Fetched: {last.papers_fetched} | New: {last.papers_new} | Ranked: {last.papers_ranked}")
        if last.digest_path:
            typer.echo(f"  Digest: {last.digest_path}")
    else:
        typer.echo("No successful runs yet.")
