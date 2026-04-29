"""HuggingFace Hub API fetcher."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


async def fetch_hf_org(
    token: str,
    org: str,
    repo_type: str = "model",
) -> list[dict]:
    """Fetch repos for a single HuggingFace org."""
    try:
        from huggingface_hub import HfApi  # type: ignore
    except ImportError:
        raise ImportError("huggingface_hub is required for HF fetching")

    api = HfApi(token=token)
    results = []

    try:
        if repo_type == "model":
            items = list(api.list_models(author=org, limit=500))
        elif repo_type == "dataset":
            items = list(api.list_datasets(author=org, limit=500))
        else:
            items = []

        for item in items:
            repo_id = getattr(item, "id", "") or getattr(item, "modelId", "")
            name_part = repo_id.split("/")[-1] if "/" in repo_id else repo_id

            tags = list(getattr(item, "tags", []) or [])
            pipeline_tag = getattr(item, "pipeline_tag", None)
            downloads = getattr(item, "downloads", 0) or 0
            likes = getattr(item, "likes", 0) or 0

            results.append({
                "id": repo_id,
                "org": org,
                "name": name_part,
                "type": repo_type,
                "downloads": downloads,
                "likes": likes,
                "tags": tags,
                "pipeline_tag": pipeline_tag,
                "assigned_domains": [],
                "score": 0.0,
                "fetched_at": datetime.now(timezone.utc),
            })
    except Exception as e:
        import sys
        print(f"Warning: HF fetch failed for {org}/{repo_type}: {e}", file=sys.stderr)

    return results


async def fetch_all_hf(token: str, orgs: list[str]) -> list[dict]:
    """Fetch models and datasets for all HF orgs."""
    all_items: dict[str, dict] = {}

    for org in orgs:
        for repo_type in ("model", "dataset"):
            try:
                items = await fetch_hf_org(token, org, repo_type)
                for item in items:
                    all_items[item["id"]] = item
            except Exception as e:
                import sys
                print(
                    f"Warning: HF fetch failed for {org}/{repo_type}: {e}",
                    file=sys.stderr,
                )

    return list(all_items.values())
