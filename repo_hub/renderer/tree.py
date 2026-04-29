"""Rich tree renderers for domain/org views."""
from __future__ import annotations

from typing import Any

from rich.tree import Tree


def domain_tree(stats: dict) -> Tree:
    """Build a Rich Tree showing repos by domain."""
    tree = Tree("[bold cyan]Domains[/bold cyan]")

    for row in stats.get("by_domain", []):
        domain = str(row.get("domain", ""))
        cnt = row.get("cnt", 0)
        avg = row.get("avg_score", 0)
        branch = tree.add(
            f"[green]{domain}[/green] — {cnt} repos, avg score: {avg}"
        )

    total = stats.get("total", 0)
    tree.add(f"[dim]Total: {total} repos[/dim]")
    return tree


def org_tree(repos: list[dict]) -> Tree:
    """Build a Rich Tree showing repos grouped by org."""
    tree = Tree("[bold cyan]Organisations[/bold cyan]")

    # Group by org
    orgs: dict[str, list[dict]] = {}
    for repo in repos:
        org = repo.get("org", "unknown")
        orgs.setdefault(org, []).append(repo)

    for org, org_repos in sorted(orgs.items(), key=lambda x: -len(x[1])):
        branch = tree.add(f"[bold]{org}[/bold] ({len(org_repos)} repos)")
        for repo in sorted(org_repos, key=lambda r: -(r.get("score", 0) or 0))[:5]:
            score = repo.get("score", 0) or 0
            name = repo.get("name", "")
            color = "green" if score >= 70 else ("yellow" if score >= 50 else "red")
            branch.add(f"[{color}]{name}[/{color}] — {score}")

    return tree
