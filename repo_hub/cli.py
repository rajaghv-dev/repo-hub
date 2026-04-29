"""repo-hub CLI — main entry point."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import click
import yaml
from dotenv import load_dotenv
from rich.console import Console

# Load .env at import time
load_dotenv()

console = Console()
err_console = Console(stderr=True)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _data_dir() -> Path:
    return Path(os.environ.get("REPO_HUB_DATA_DIR", "./data"))


def _config_dir() -> Path:
    return Path(os.environ.get("REPO_HUB_CONFIG_DIR", "./config"))


def _load_orgs_config() -> dict:
    path = _config_dir() / "orgs.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def _load_ontology():
    from repo_hub.classifier.ontology_loader import load_ontology
    return load_ontology(_config_dir() / "ontology.yaml")


def _load_profile() -> dict:
    path = _config_dir() / "profile.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def _parse_since(since: str) -> datetime:
    """Parse '7d', '30d', '1h' etc. into a datetime."""
    now = datetime.now(timezone.utc)
    if since.endswith("d"):
        days = int(since[:-1])
        return now - timedelta(days=days)
    elif since.endswith("h"):
        hours = int(since[:-1])
        return now - timedelta(hours=hours)
    elif since.endswith("w"):
        weeks = int(since[:-1])
        return now - timedelta(weeks=weeks)
    else:
        # Try ISO format
        return datetime.fromisoformat(since)


async def _get_conn():
    """Get a single async connection."""
    import psycopg
    dsn = os.environ.get("DATABASE_URL", "")
    conn = await psycopg.AsyncConnection.connect(dsn, row_factory=None)
    return conn


# ── Main CLI group ────────────────────────────────────────────────────────────


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """repo-hub — personal second brain for GitHub repositories."""
    ctx.ensure_object(dict)


# ── doctor ────────────────────────────────────────────────────────────────────


@cli.command()
def doctor() -> None:
    """Check GitHub token, HF token, PG connection, GCS access, bge-small model."""
    import httpx

    all_ok = True

    # GitHub
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        err_console.print("[red]GITHUB_TOKEN not set[/red]")
        all_ok = False
    else:
        try:
            resp = httpx.get(
                "https://api.github.com/rate_limit",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            data = resp.json()
            remaining = data.get("rate", {}).get("remaining", "?")
            console.print(f"[green]GitHub token OK[/green] — rate limit remaining: {remaining}")
        except Exception as e:
            err_console.print(f"[red]GitHub token check failed: {e}[/red]")
            all_ok = False

    # HF Token
    hf_token = os.environ.get("HF_TOKEN", "")
    if hf_token:
        console.print("[green]HF_TOKEN set[/green]")
    else:
        console.print("[yellow]HF_TOKEN not set (optional)[/yellow]")

    # PostgreSQL
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        err_console.print("[red]DATABASE_URL not set[/red]")
        all_ok = False
    else:
        try:
            import psycopg
            conn = psycopg.connect(db_url)
            cur = conn.cursor()
            cur.execute("SELECT version()")
            ver = cur.fetchone()[0][:50]
            console.print(f"[green]PostgreSQL OK[/green] — {ver}")
            # Check extensions
            cur.execute("SELECT extname FROM pg_extension WHERE extname IN ('vector','pg_trgm')")
            exts = [r[0] for r in cur.fetchall()]
            for ext in ("vector", "pg_trgm"):
                if ext in exts:
                    console.print(f"  [green]{ext} extension OK[/green]")
                else:
                    console.print(f"  [yellow]{ext} extension not found[/yellow]")
            conn.close()
        except Exception as e:
            err_console.print(f"[red]PostgreSQL check failed: {e}[/red]")
            all_ok = False

    # GCS
    gcs_bucket = os.environ.get("REPO_HUB_GCS_BUCKET", "")
    if not gcs_bucket:
        console.print("[yellow]REPO_HUB_GCS_BUCKET not set (optional)[/yellow]")
    else:
        try:
            from google.cloud import storage  # type: ignore
            client = storage.Client()
            bucket = client.bucket(gcs_bucket)
            bucket.reload()
            console.print(f"[green]GCS OK[/green] — bucket: {gcs_bucket}")
        except Exception as e:
            err_console.print(f"[red]GCS check failed: {e}[/red]")
            all_ok = False

    # bge-small model
    console.print("[dim]Checking bge-small model (may download ~22MB)...[/dim]")
    try:
        from repo_hub.embedder.embedder import Embedder
        emb = Embedder()
        vec = emb.embed(["test"])
        console.print(f"[green]bge-small OK[/green] — vector dim: {len(vec[0])}")
    except Exception as e:
        err_console.print(f"[red]bge-small model check failed: {e}[/red]")
        all_ok = False

    if all_ok:
        console.print("\n[bold green]All checks passed.[/bold green]")
    else:
        console.print("\n[bold red]Some checks failed.[/bold red]")
        sys.exit(1)


# ── db group ──────────────────────────────────────────────────────────────────


@cli.group()
def db() -> None:
    """Database management commands."""


@db.command("init")
def db_init() -> None:
    """Run schema.sql against DATABASE_URL."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        err_console.print("[red]DATABASE_URL not set[/red]")
        sys.exit(1)

    schema_path = Path(__file__).parent.parent / "schema.sql"
    if not schema_path.exists():
        err_console.print(f"[red]schema.sql not found at {schema_path}[/red]")
        sys.exit(1)

    try:
        import psycopg
        conn = psycopg.connect(db_url, autocommit=True)
        sql = schema_path.read_text()
        conn.execute(sql)
        conn.close()
        console.print("[green]Database schema initialized successfully.[/green]")
    except Exception as e:
        err_console.print(f"[red]Schema init failed: {e}[/red]")
        sys.exit(1)


# ── restore ───────────────────────────────────────────────────────────────────


@cli.command()
def restore() -> None:
    """Pull GCS cache to local data/ directory."""
    bucket = os.environ.get("REPO_HUB_GCS_BUCKET", "")
    prefix = os.environ.get("REPO_HUB_GCS_PREFIX", "repo-hub/")
    if not bucket:
        err_console.print("[red]REPO_HUB_GCS_BUCKET not set[/red]")
        sys.exit(1)

    data_dir = _data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    try:
        from repo_hub.storage.gcs import GCSStore
        store = GCSStore(bucket, prefix)
        count = store.restore(data_dir)
        console.print(f"[green]Restored {count} files from GCS.[/green]")
    except Exception as e:
        err_console.print(f"[red]Restore failed: {e}[/red]")
        sys.exit(1)


# ── fetch ─────────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--org", multiple=True, help="Fetch only these orgs")
@click.option("--sample", type=int, default=None, help="Max repos per org")
@click.option("--incremental", is_flag=True, help="Skip cache-fresh orgs")
def fetch(org: tuple, sample: int | None, incremental: bool) -> None:
    """Fetch GitHub repos for all tracked orgs."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        err_console.print("[red]GITHUB_TOKEN not set[/red]")
        sys.exit(1)

    orgs_config_data = _load_orgs_config()
    all_orgs = orgs_config_data.get("orgs", [])
    defaults = orgs_config_data.get("defaults", {})

    if org:
        all_orgs = [o for o in all_orgs if o["handle"] in org]

    cache = __import__("repo_hub.storage.cache", fromlist=["Cache"]).Cache(
        _data_dir()
    )

    async def _run() -> None:
        from repo_hub.fetcher.github_client import GitHubClient
        from repo_hub.fetcher.org_fetcher import fetch_all

        from rich.progress import Progress, SpinnerColumn, TextColumn

        async with GitHubClient(token) as client:
            with Progress(SpinnerColumn(), TextColumn("{task.description}")) as progress:
                task = progress.add_task("Fetching orgs...", total=len(all_orgs))

                all_repos = []
                for org_cfg in all_orgs:
                    if incremental and cache.is_fresh(org_cfg["handle"]):
                        progress.advance(task)
                        continue
                    progress.update(task, description=f"Fetching {org_cfg['handle']}...")
                    try:
                        repos = await __import__(
                            "repo_hub.fetcher.org_fetcher", fromlist=["fetch_org"]
                        ).fetch_org(client, cache, org_cfg, defaults)
                        all_repos.extend(repos)
                    except Exception as e:
                        err_console.print(f"[yellow]Warning: {org_cfg['handle']}: {e}[/yellow]")
                    progress.advance(task)

        console.print(f"[green]Fetched {len(all_repos)} repos.[/green]")

    asyncio.run(_run())


# ── hf ────────────────────────────────────────────────────────────────────────


@cli.command()
def hf() -> None:
    """Fetch HuggingFace Hub repos."""
    token = os.environ.get("HF_TOKEN", "")
    orgs_config_data = _load_orgs_config()
    hf_orgs = orgs_config_data.get("hf_orgs", [])

    async def _run() -> None:
        from repo_hub.fetcher.hf_fetcher import fetch_all_hf
        console.print(f"[dim]Fetching HF repos for {len(hf_orgs)} orgs...[/dim]")
        repos = await fetch_all_hf(token, hf_orgs)
        console.print(f"[green]Fetched {len(repos)} HuggingFace repos.[/green]")

    asyncio.run(_run())


# ── classify ──────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--org", multiple=True)
@click.option("--sample", type=int, default=None)
def classify(org: tuple, sample: int | None) -> None:
    """Classify repos from cache into PostgreSQL."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        err_console.print("[red]DATABASE_URL not set[/red]")
        sys.exit(1)

    domains, ont_config = _load_ontology()
    threshold = ont_config.get("threshold", 0.15)
    cache = __import__("repo_hub.storage.cache", fromlist=["Cache"]).Cache(_data_dir())

    orgs_config_data = _load_orgs_config()
    all_orgs = orgs_config_data.get("orgs", [])
    defaults = orgs_config_data.get("defaults", {})
    if org:
        all_orgs = [o for o in all_orgs if o["handle"] in org]

    async def _run() -> None:
        import psycopg
        from repo_hub.classifier.domain_classifier import classify_batch
        from repo_hub.storage.db import upsert_repos

        conn = await psycopg.AsyncConnection.connect(db_url)

        all_repos = []
        for org_cfg in all_orgs:
            cached = cache.get(org_cfg["handle"])
            if cached:
                all_repos.extend(cached)

        if sample:
            all_repos = all_repos[:sample]

        console.print(f"[dim]Classifying {len(all_repos)} repos...[/dim]")
        classified = classify_batch(all_repos, domains, ont_config, threshold)
        count = await upsert_repos(conn, classified)
        await conn.commit()
        await conn.close()
        console.print(f"[green]Classified and upserted {count} repos.[/green]")

    asyncio.run(_run())


# ── embed ─────────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--skip-existing", is_flag=True, default=True, help="Skip already embedded repos")
def embed(skip_existing: bool) -> None:
    """Generate embeddings for classified repos."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        err_console.print("[red]DATABASE_URL not set[/red]")
        sys.exit(1)

    async def _run() -> None:
        import psycopg
        from repo_hub.embedder.embedder import Embedder, embed_repos
        from psycopg.rows import dict_row

        conn = await psycopg.AsyncConnection.connect(db_url)

        # Fetch repos needing embedding
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT id, name, description FROM repos WHERE score > 0 ORDER BY score DESC"
            )
            repos = [dict(r) for r in await cur.fetchall()]

        console.print(f"[dim]Embedding {len(repos)} repos...[/dim]")
        embedder = Embedder()
        count = await embed_repos(embedder, conn, repos)
        await conn.commit()
        await conn.close()
        console.print(f"[green]Embedded {count} repos.[/green]")

    asyncio.run(_run())


# ── score ─────────────────────────────────────────────────────────────────────


@cli.command()
def score() -> None:
    """Compute composite scores for all classified repos."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        err_console.print("[red]DATABASE_URL not set[/red]")
        sys.exit(1)

    domains, ont_config = _load_ontology()
    profile = _load_profile()
    saturation = ont_config.get("saturation", {})

    async def _run() -> None:
        import psycopg
        from repo_hub.scorer.composite_scorer import score_batch
        from repo_hub.storage.db import upsert_repos
        from psycopg.rows import dict_row

        conn = await psycopg.AsyncConnection.connect(db_url)
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT * FROM repos WHERE assigned_domains != '[]'::jsonb")
            repos = [dict(r) for r in await cur.fetchall()]

        console.print(f"[dim]Scoring {len(repos)} repos...[/dim]")
        scored = score_batch(repos, profile, domains, saturation)
        count = await upsert_repos(conn, scored)
        await conn.commit()
        await conn.close()
        console.print(f"[green]Scored {count} repos.[/green]")

    asyncio.run(_run())


# ── digest ────────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--since", default="7d", help="Time window e.g. 7d, 24h")
@click.option("--domain", multiple=True, help="Filter by domain")
def digest(since: str, domain: tuple) -> None:
    """Show recent changes digest."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        err_console.print("[red]DATABASE_URL not set[/red]")
        sys.exit(1)

    since_dt = _parse_since(since)

    async def _run() -> None:
        import psycopg
        from repo_hub.storage.db import get_digest
        from repo_hub.renderer.table import digest_table

        conn = await psycopg.AsyncConnection.connect(db_url)
        domain_filter = domain[0] if len(domain) == 1 else None
        events = await get_digest(conn, since_dt, domain_filter)
        await conn.close()

        if not events:
            console.print("[dim]No events found.[/dim]")
            return

        table = digest_table(events)
        console.print(table)

    asyncio.run(_run())


# ── export ────────────────────────────────────────────────────────────────────


@cli.command()
def export() -> None:
    """Export repos to Parquet/CSV and push to GCS."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        err_console.print("[red]DATABASE_URL not set[/red]")
        sys.exit(1)

    bucket = os.environ.get("REPO_HUB_GCS_BUCKET", "")
    prefix = os.environ.get("REPO_HUB_GCS_PREFIX", "repo-hub/")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    export_dir = _data_dir() / "exports" / today
    export_dir.mkdir(parents=True, exist_ok=True)

    async def _run() -> None:
        import psycopg
        from psycopg.rows import dict_row
        from repo_hub.renderer.export import to_parquet, to_csv, to_json_summary
        from repo_hub.storage.db import get_stats

        conn = await psycopg.AsyncConnection.connect(db_url)
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT * FROM repos ORDER BY score DESC")
            repos = [dict(r) for r in await cur.fetchall()]

        stats = await get_stats(conn)
        await conn.close()

        to_parquet(repos, export_dir / "repos.parquet")
        to_csv(repos, export_dir / "repos.csv")
        to_json_summary(repos, export_dir / "summary.json")
        console.print(f"[green]Exported {len(repos)} repos to {export_dir}[/green]")

        if bucket:
            from repo_hub.storage.gcs import GCSStore
            store = GCSStore(bucket, prefix)
            count = store.push_dir(export_dir, f"exports/{today}")
            console.print(f"[green]Pushed {count} files to GCS.[/green]")

    asyncio.run(_run())


# ── report ────────────────────────────────────────────────────────────────────


@cli.command()
def report() -> None:
    """Generate REPORT.md."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        err_console.print("[red]DATABASE_URL not set[/red]")
        sys.exit(1)

    async def _run() -> None:
        import psycopg
        from psycopg.rows import dict_row
        from repo_hub.renderer.export import generate_report
        from repo_hub.storage.db import get_stats

        conn = await psycopg.AsyncConnection.connect(db_url)
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT * FROM repos WHERE score > 0 ORDER BY score DESC")
            repos = [dict(r) for r in await cur.fetchall()]

        stats = await get_stats(conn)
        await conn.close()

        output_path = Path("REPORT.md")
        generate_report(repos, stats, output_path)
        console.print(f"[green]Report written to {output_path}[/green]")

    asyncio.run(_run())


# ── push ──────────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--clean", is_flag=True, help="Delete local data/ after push")
def push(clean: bool) -> None:
    """Sync local data to GCS and git push REPORT.md."""
    bucket = os.environ.get("REPO_HUB_GCS_BUCKET", "")
    prefix = os.environ.get("REPO_HUB_GCS_PREFIX", "repo-hub/")

    if bucket:
        try:
            from repo_hub.storage.gcs import GCSStore
            store = GCSStore(bucket, prefix)
            data_dir = _data_dir()
            count = store.push_dir(data_dir, "cache")
            console.print(f"[green]Pushed {count} files to GCS.[/green]")
        except Exception as e:
            err_console.print(f"[red]GCS push failed: {e}[/red]")

    # Git push REPORT.md if it exists
    import subprocess
    if Path("REPORT.md").exists():
        try:
            subprocess.run(["git", "add", "REPORT.md"], check=True, capture_output=True)
            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                capture_output=True,
            )
            if result.returncode != 0:
                subprocess.run(
                    ["git", "commit", "-m", "chore: update REPORT.md"],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(["git", "push"], check=True, capture_output=True)
                console.print("[green]Git push complete.[/green]")
        except subprocess.CalledProcessError as e:
            err_console.print(f"[yellow]Git push skipped: {e}[/yellow]")

    if clean:
        import shutil
        data_dir = _data_dir()
        if data_dir.exists():
            shutil.rmtree(data_dir)
            console.print(f"[green]Deleted {data_dir}[/green]")


# ── all ───────────────────────────────────────────────────────────────────────


@cli.command("all")
@click.option("--clean", is_flag=True, help="Delete local data/ after run")
@click.option("--sample", type=int, default=None)
@click.option("--incremental", is_flag=True)
def all_cmd(clean: bool, sample: int | None, incremental: bool) -> None:
    """Run the full pipeline: fetch → classify → embed → score → export → push."""
    from click.testing import CliRunner

    ctx = click.get_current_context()

    steps = [
        ("restore", []),
        ("fetch", ["--sample", str(sample)] if sample else (["--incremental"] if incremental else [])),
        ("hf", []),
        ("classify", ["--sample", str(sample)] if sample else []),
        ("embed", []),
        ("score", []),
        ("digest", []),
        ("export", []),
        ("report", []),
        ("push", ["--clean"] if clean else []),
    ]

    for cmd_name, args in steps:
        cmd = cli.get_command(ctx, cmd_name)
        if cmd is None:
            continue
        console.print(f"[cyan]→ repo-hub {cmd_name}[/cyan]")
        try:
            ctx2 = cmd.make_context(cmd_name, list(args), parent=ctx)
            cmd.invoke(ctx2)
        except SystemExit as e:
            if e.code != 0:
                err_console.print(f"[red]Step '{cmd_name}' failed.[/red]")
                sys.exit(1)
        except Exception as e:
            err_console.print(f"[red]Step '{cmd_name}' error: {e}[/red]")
            sys.exit(1)


# ── list ──────────────────────────────────────────────────────────────────────


@cli.command("list")
@click.option("--domain", multiple=True)
@click.option("--org", multiple=True)
@click.option("--min-score", type=float, default=0)
@click.option("--top", type=int, default=50)
@click.option("--status")
@click.option("--sort", default="score", type=click.Choice(["score", "stars", "pushed"]))
@click.option("--active", is_flag=True)
@click.option("--tag")
def list_cmd(
    domain: tuple,
    org: tuple,
    min_score: float,
    top: int,
    status: str | None,
    sort: str,
    active: bool,
    tag: str | None,
) -> None:
    """List repos from PostgreSQL with filters."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        err_console.print("[red]DATABASE_URL not set[/red]")
        sys.exit(1)

    async def _run() -> None:
        import psycopg
        from repo_hub.storage.db import get_repos
        from repo_hub.renderer.table import repos_table

        conn = await psycopg.AsyncConnection.connect(db_url)
        filters: dict[str, Any] = {
            "min_score": min_score,
            "sort": sort,
            "limit": top,
        }
        if domain:
            filters["domain"] = list(domain)
        if org:
            filters["org"] = list(org)
        if status:
            filters["status"] = status
        if active:
            filters["active"] = True
        if tag:
            filters["tag"] = tag

        repos = await get_repos(conn, **filters)
        await conn.close()

        if not repos:
            console.print("[dim]No repos found.[/dim]")
            return

        table = repos_table(repos)
        console.print(table)
        console.print(f"[dim]{len(repos)} repos[/dim]")

    asyncio.run(_run())


# ── show ──────────────────────────────────────────────────────────────────────


@cli.command()
@click.argument("repo_id")
@click.option("--explain", is_flag=True)
def show(repo_id: str, explain: bool) -> None:
    """Show detailed information for a single repo."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        err_console.print("[red]DATABASE_URL not set[/red]")
        sys.exit(1)

    async def _run() -> None:
        import psycopg
        from repo_hub.storage.db import get_repo, get_user_data
        from repo_hub.renderer.table import repo_detail

        conn = await psycopg.AsyncConnection.connect(db_url)
        repo = await get_repo(conn, repo_id)
        user_data = await get_user_data(conn, repo_id) if repo else None
        await conn.close()

        if not repo:
            err_console.print(f"[red]Repo not found: {repo_id}[/red]")
            sys.exit(1)

        panel = repo_detail(repo, user_data, explain=explain)
        console.print(panel)

    asyncio.run(_run())


# ── search ────────────────────────────────────────────────────────────────────


@cli.command()
@click.argument("query")
@click.option("--limit", default=20)
@click.option("--domain", multiple=True)
@click.option("--min-stars", type=int, default=0)
def search(query: str, limit: int, domain: tuple, min_stars: int) -> None:
    """Semantic + full-text search across repos."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        err_console.print("[red]DATABASE_URL not set[/red]")
        sys.exit(1)

    async def _run() -> None:
        import psycopg
        from repo_hub.storage.db import semantic_search, fts_search
        from repo_hub.renderer.table import repos_table

        conn = await psycopg.AsyncConnection.connect(db_url)

        # Try semantic search first (requires embeddings)
        results = []
        try:
            from repo_hub.embedder.embedder import Embedder
            embedder = Embedder()
            vec = embedder.embed([query])[0]
            results = await semantic_search(conn, vec, limit=limit)
        except Exception:
            pass

        # Fall back to FTS if no semantic results
        if not results:
            results = await fts_search(conn, query, limit=limit)

        await conn.close()

        if not results:
            console.print("[dim]No results.[/dim]")
            return

        table = repos_table(results, show_scores=True)
        console.print(table)

    asyncio.run(_run())


# ── stats ─────────────────────────────────────────────────────────────────────


@cli.command()
@click.option("--domain")
@click.option("--org")
def stats(domain: str | None, org: str | None) -> None:
    """Show domain and org statistics."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        err_console.print("[red]DATABASE_URL not set[/red]")
        sys.exit(1)

    async def _run() -> None:
        import psycopg
        from repo_hub.storage.db import get_stats
        from repo_hub.renderer.table import stats_table
        from repo_hub.renderer.tree import domain_tree

        conn = await psycopg.AsyncConnection.connect(db_url)
        stats_data = await get_stats(conn, domain=domain)
        await conn.close()

        tree = domain_tree(stats_data)
        console.print(tree)

        table = stats_table(stats_data)
        console.print(table)

    asyncio.run(_run())


# ── annotate ──────────────────────────────────────────────────────────────────


@cli.command()
@click.argument("repo_id")
@click.option("--status", type=click.Choice(["new", "reviewing", "bookmarked", "in-use", "dismissed"]))
@click.option("--tags")
@click.option("--note")
@click.option("--project")
@click.option("--priority", type=int)
def annotate(
    repo_id: str,
    status: str | None,
    tags: str | None,
    note: str | None,
    project: str | None,
    priority: int | None,
) -> None:
    """Annotate a repo with status, tags, notes."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        err_console.print("[red]DATABASE_URL not set[/red]")
        sys.exit(1)

    async def _run() -> None:
        import psycopg
        from repo_hub.storage.db import upsert_user_data

        kwargs: dict[str, Any] = {}
        if status:
            kwargs["status"] = status
        if tags:
            kwargs["tags"] = [t.strip() for t in tags.split(",")]
        if note:
            kwargs["notes"] = note
        if project:
            kwargs["projects"] = [project]
        if priority is not None:
            kwargs["priority"] = priority

        conn = await psycopg.AsyncConnection.connect(db_url)
        await upsert_user_data(conn, repo_id, **kwargs)
        await conn.commit()
        await conn.close()
        console.print(f"[green]Annotated {repo_id}[/green]")

    asyncio.run(_run())


# ── orgs group ────────────────────────────────────────────────────────────────


@cli.group()
def orgs() -> None:
    """Manage tracked orgs."""


@orgs.command("list")
def orgs_list() -> None:
    """List all tracked orgs."""
    config = _load_orgs_config()
    all_orgs = config.get("orgs", [])

    table = __import__("rich.table", fromlist=["Table"]).Table(
        show_header=True, header_style="bold cyan"
    )
    table.add_column("Handle", min_width=25)
    table.add_column("Label", min_width=25)
    table.add_column("Type", min_width=8)

    for org_cfg in all_orgs:
        table.add_row(
            org_cfg.get("handle", ""),
            org_cfg.get("label", ""),
            org_cfg.get("type", "org"),
        )

    console.print(table)
    console.print(f"[dim]{len(all_orgs)} orgs total[/dim]")


@orgs.command("add")
@click.argument("handle")
@click.option("--label")
@click.option("--type", "org_type", default="org")
@click.option("--min-stars", type=int)
def orgs_add(
    handle: str,
    label: str | None,
    org_type: str,
    min_stars: int | None,
) -> None:
    """Add a new org to config/orgs.yaml."""
    config_path = _config_dir() / "orgs.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Check if already exists
    existing = {o["handle"] for o in config.get("orgs", [])}
    if handle in existing:
        err_console.print(f"[yellow]Org {handle} already tracked.[/yellow]")
        return

    new_org: dict[str, Any] = {
        "handle": handle,
        "label": label or handle,
        "type": org_type,
    }
    if min_stars is not None:
        new_org["min_stars"] = min_stars

    config.setdefault("orgs", []).append(new_org)

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    console.print(f"[green]Added org: {handle}[/green]")


# ── ontology ──────────────────────────────────────────────────────────────────


@cli.command()
def ontology() -> None:
    """Show domain ontology summary."""
    domains, config = _load_ontology()

    from rich.table import Table

    table = Table(show_header=True, header_style="bold cyan", title="21-Domain Ontology")
    table.add_column("ID", min_width=20)
    table.add_column("Label", min_width=25)
    table.add_column("Group", min_width=10)
    table.add_column("Profile", min_width=10)
    table.add_column("Signals", justify="right")

    for domain in domains:
        sig_count = (
            len(domain.signals.topics)
            + len(domain.signals.description)
            + len(domain.signals.deps)
            + len(domain.signals.filenames)
        )
        table.add_row(
            domain.id,
            domain.label,
            domain.group,
            domain.weight_profile,
            str(sig_count),
        )

    console.print(table)
    console.print(f"[dim]Threshold: {config['threshold']}[/dim]")


# ── profile ───────────────────────────────────────────────────────────────────


@cli.command()
def profile() -> None:
    """Show current scoring profile."""
    profile_data = _load_profile()

    from rich.table import Table

    table = Table(show_header=True, header_style="bold cyan", title="Domain Weights")
    table.add_column("Domain", min_width=25)
    table.add_column("Weight", justify="right")

    for domain_id, weight in sorted(
        profile_data.get("domain_weights", {}).items(),
        key=lambda x: -x[1],
    ):
        color = "green" if weight >= 2.5 else ("yellow" if weight >= 1.5 else "dim")
        table.add_row(domain_id, f"[{color}]{weight}[/{color}]")

    console.print(table)

    console.print("\n[bold]Scoring weights:[/bold]")
    for k, v in profile_data.get("scoring_weights", {}).items():
        console.print(f"  {k}: {v}")

    console.print("\n[bold]Tech interests:[/bold]")
    interests = profile_data.get("tech_interests", [])
    console.print(f"  {', '.join(interests)}")

    console.print("\n[bold]Priority orgs:[/bold]")
    priority = profile_data.get("priority_orgs", [])
    console.print(f"  {', '.join(priority)}")
