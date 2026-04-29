"""Rich-based table and panel renderers."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def _score_color(score: float) -> str:
    """Color-code a score: green>=70, yellow>=50, red<50."""
    if score >= 70:
        return "green"
    elif score >= 50:
        return "yellow"
    return "red"


def _format_domains(domains: Any) -> str:
    """Format domain list as compact badges."""
    if not domains:
        return ""
    if isinstance(domains, str):
        import json
        try:
            domains = json.loads(domains)
        except Exception:
            return domains
    return ", ".join(str(d) for d in domains[:3])


def _format_stars(stars: int) -> str:
    if stars >= 1000:
        return f"{stars / 1000:.1f}k"
    return str(stars)


def repos_table(
    repos: list[dict],
    show_scores: bool = True,
    show_domain: bool = True,
) -> Table:
    """Build a Rich Table from a list of repo dicts."""
    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        expand=False,
    )

    table.add_column("Repo", min_width=30, no_wrap=True)
    table.add_column("Stars", justify="right", min_width=6)
    if show_domain:
        table.add_column("Domains", min_width=20)
    if show_scores:
        table.add_column("Score", justify="right", min_width=6)
    table.add_column("Lang", min_width=10)
    table.add_column("Status", min_width=10)

    for repo in repos:
        repo_id = repo.get("id", "")
        stars = repo.get("stars", 0) or 0
        score_val = repo.get("score", 0.0) or 0.0
        lang = repo.get("language") or ""
        status = repo.get("status") or ""

        domains_str = _format_domains(repo.get("assigned_domains", []))

        score_text = Text(str(score_val), style=_score_color(score_val))
        status_style = {
            "bookmarked": "bold blue",
            "in-use": "bold green",
            "reviewing": "yellow",
            "dismissed": "dim",
            "new": "white",
        }.get(status, "white")

        row = [repo_id, _format_stars(stars)]
        if show_domain:
            row.append(domains_str)
        if show_scores:
            row.append(score_text)
        row.extend([lang, Text(status, style=status_style)])

        table.add_row(*row)

    return table


def repo_detail(
    repo: dict,
    user_data: dict | None = None,
    explain: bool = False,
) -> Panel:
    """Build a Rich Panel with detailed repo information."""
    from rich.markdown import Markdown

    repo_id = repo.get("id", "unknown")
    score_val = repo.get("score", 0.0) or 0.0
    color = _score_color(score_val)

    lines = []
    lines.append(f"[bold]{repo_id}[/bold]  [link={repo.get('url', '')}]{repo.get('url', '')}[/link]")
    lines.append(f"[dim]{repo.get('description', '') or ''}[/dim]")
    lines.append("")
    lines.append(
        f"[bold {color}]Score: {score_val}[/bold {color}]  "
        f"Stars: {_format_stars(repo.get('stars', 0) or 0)}  "
        f"Lang: {repo.get('language', '') or ''}  "
        f"License: {repo.get('license', '') or 'none'}"
    )

    domains = repo.get("assigned_domains", [])
    if isinstance(domains, str):
        import json
        try:
            domains = json.loads(domains)
        except Exception:
            domains = []
    if domains:
        lines.append(f"Domains: {', '.join(domains)}")

    if explain:
        lines.append("")
        lines.append("[bold]Score Breakdown:[/bold]")
        lines.append(f"  S_activity : {repo.get('s_activity', 0):.3f}")
        lines.append(f"  S_ontology : {repo.get('s_ontology', 0):.3f}")
        lines.append(f"  S_deps     : {repo.get('s_deps', 0):.3f}")
        lines.append(f"  S_profile  : {repo.get('s_profile', 0):.3f}")

        matched = repo.get("matched_signals", {})
        if isinstance(matched, str):
            import json
            try:
                matched = json.loads(matched)
            except Exception:
                matched = {}
        if matched:
            lines.append("")
            lines.append("[bold]Matched Signals:[/bold]")
            for domain_id, signals in matched.items():
                lines.append(f"  [{domain_id}]: {', '.join(signals[:5])}")

        deps = repo.get("extracted_deps", {})
        if isinstance(deps, str):
            import json
            try:
                deps = json.loads(deps)
            except Exception:
                deps = {}
        if deps:
            lines.append("")
            lines.append("[bold]Extracted Deps:[/bold]")
            for fname, dep_list in list(deps.items())[:4]:
                lines.append(f"  {fname}: {', '.join(dep_list[:5])}")

    if user_data:
        lines.append("")
        lines.append("[bold]Your Notes:[/bold]")
        lines.append(f"  Status  : {user_data.get('status', 'new')}")
        tags = user_data.get("tags", [])
        if isinstance(tags, str):
            import json
            try:
                tags = json.loads(tags)
            except Exception:
                tags = []
        if tags:
            lines.append(f"  Tags    : {', '.join(tags)}")
        if user_data.get("notes"):
            lines.append(f"  Notes   : {user_data['notes'][:200]}")

    content = "\n".join(lines)
    return Panel(content, title=repo_id, border_style=color)


def stats_table(stats: dict) -> Table:
    """Build a Rich Table from stats dict."""
    table = Table(
        title="Domain Statistics",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Domain", min_width=25)
    table.add_column("Repos", justify="right")
    table.add_column("Avg Score", justify="right")
    table.add_column("Top Score", justify="right")

    for row in stats.get("by_domain", []):
        table.add_row(
            str(row.get("domain", "")),
            str(row.get("cnt", 0)),
            str(row.get("avg_score", 0)),
            str(row.get("top_score", 0)),
        )

    return table


def digest_table(events: list[dict]) -> Table:
    """Build a Rich Table from digest events."""
    table = Table(
        title="Recent Changes",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("When", min_width=12)
    table.add_column("Repo", min_width=30)
    table.add_column("Event", min_width=15)
    table.add_column("Detail", min_width=30)

    for event in events:
        detected_at = event.get("detected_at")
        if isinstance(detected_at, datetime):
            when = detected_at.strftime("%m-%d %H:%M")
        else:
            when = str(detected_at or "")[:16]

        repo_id = f"{event.get('org', '')}/{event.get('name', '')}"
        evt = str(event.get("event", ""))
        detail = event.get("detail", {})
        if isinstance(detail, str):
            import json
            try:
                detail = json.loads(detail)
            except Exception:
                detail = {}
        detail_str = ", ".join(f"{k}:{v}" for k, v in list(detail.items())[:3])

        table.add_row(when, repo_id, evt, detail_str)

    return table
