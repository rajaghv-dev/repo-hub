"""Fetch repos for all configured orgs from GitHub API."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from repo_hub.fetcher.github_client import GitHubClient
from repo_hub.storage.cache import Cache


def _normalize_repo(raw: dict, org_handle: str) -> dict:
    """Convert a raw GitHub API repo dict to our normalized schema."""
    license_info = raw.get("license") or {}
    license_spdx = license_info.get("spdx_id") if license_info else None
    if license_spdx in ("NOASSERTION", "OTHER", ""):
        license_spdx = None

    pushed_at = raw.get("pushed_at")
    if isinstance(pushed_at, str):
        try:
            pushed_at = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
        except ValueError:
            pushed_at = None

    return {
        "id": f"{org_handle}/{raw['name']}",
        "org": org_handle,
        "name": raw["name"],
        "url": raw.get("html_url"),
        "description": raw.get("description") or "",
        "stars": raw.get("stargazers_count", 0),
        "forks": raw.get("forks_count", 0),
        "open_issues": raw.get("open_issues_count", 0),
        "language": raw.get("language"),
        "license": license_spdx,
        "last_pushed_at": pushed_at,
        "is_archived": raw.get("archived", False),
        "is_fork": raw.get("fork", False),
        "topics": raw.get("topics", []),
        "assigned_domains": [],
        "extracted_deps": {},
        "s_activity": 0.0,
        "s_ontology": 0.0,
        "s_deps": 0.0,
        "s_profile": 0.0,
        "score": 0.0,
        "matched_signals": {},
        "source": "github",
        "classified_at": None,
        "fetched_at": datetime.now(timezone.utc),
    }


def _apply_filters(repos: list[dict], org_config: dict, defaults: dict) -> list[dict]:
    """Apply per-org and default filters."""
    min_stars = org_config.get("min_stars", defaults.get("min_stars", 10))
    include_forks = org_config.get(
        "include_forks", defaults.get("include_forks", False)
    )
    filter_topics = set(org_config.get("filter_topics", []))
    filter_repos = set(org_config.get("filter_repos", []))
    max_repos = org_config.get(
        "max_repos_per_org", defaults.get("max_repos_per_org", 500)
    )

    filtered = []
    for repo in repos:
        if repo["stars"] < min_stars:
            continue
        if not include_forks and repo["is_fork"]:
            continue
        if filter_repos and repo["name"] not in filter_repos:
            continue
        if filter_topics:
            repo_topics = set(repo.get("topics", []))
            if not repo_topics.intersection(filter_topics):
                continue
        filtered.append(repo)
        if len(filtered) >= max_repos:
            break

    return filtered


async def fetch_org(
    client: GitHubClient,
    cache: Cache,
    org_config: dict,
    defaults: dict | None = None,
) -> list[dict]:
    """Fetch all repos for a single org, using cache if fresh."""
    if defaults is None:
        defaults = {}
    handle = org_config["handle"]
    org_type = org_config.get("type", "org")

    # Return from cache if still fresh
    cached = cache.get(handle)
    if cached is not None:
        return _apply_filters(cached, org_config, defaults)

    # Fetch from GitHub API
    if org_type == "user":
        url = f"/users/{handle}/repos"
    else:
        url = f"/orgs/{handle}/repos"

    params = {"type": "public", "per_page": 100}
    raw_repos = []
    async for repo in client.paginate(url, params):
        normalized = _normalize_repo(repo, handle)
        raw_repos.append(normalized)

    # Write all (unfiltered) to cache
    cache.put(handle, raw_repos)

    return _apply_filters(raw_repos, org_config, defaults)


async def fetch_all(
    client: GitHubClient,
    cache: Cache,
    orgs_config: list[dict],
    defaults: dict | None = None,
    sample: int | None = None,
) -> list[dict]:
    """Fetch repos for all orgs. Returns deduplicated list."""
    if defaults is None:
        defaults = {}

    all_repos: dict[str, dict] = {}
    orgs_to_fetch = orgs_config[:sample] if sample else orgs_config

    # Process orgs sequentially to respect rate limits
    for org_config in orgs_to_fetch:
        try:
            repos = await fetch_org(client, cache, org_config, defaults)
            for repo in repos:
                all_repos[repo["id"]] = repo
        except Exception as e:
            # Log but don't abort the whole run
            import sys
            print(f"Warning: failed to fetch {org_config.get('handle')}: {e}", file=sys.stderr)

    return list(all_repos.values())
