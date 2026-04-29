"""Activity sub-score computation."""
from __future__ import annotations

import math
from datetime import datetime, timezone


def score_activity(repo: dict) -> float:
    """
    Compute S_activity in [0, 1].

    Formula:
        recency   = max(0, 1 - days_since_last_push / 730)
        star_vel  = stars / max(1, repo_age_days / 30)
        star_score = log10(1 + min(star_vel, 1000)) / log10(1001)
        issue_sig = min(1.0, open_issues / 50)
        S_activity = 0.50 * recency + 0.35 * star_score + 0.15 * issue_sig

    Archived repos return 0.0.
    """
    if repo.get("is_archived", False):
        return 0.0

    now = datetime.now(timezone.utc)

    # Recency
    last_pushed = repo.get("last_pushed_at")
    if last_pushed is None:
        days_since_push = 730  # assume stale
    else:
        if isinstance(last_pushed, str):
            try:
                last_pushed = datetime.fromisoformat(
                    last_pushed.replace("Z", "+00:00")
                )
            except ValueError:
                last_pushed = None

        if last_pushed is None:
            days_since_push = 730
        else:
            if last_pushed.tzinfo is None:
                last_pushed = last_pushed.replace(tzinfo=timezone.utc)
            days_since_push = max(0, (now - last_pushed).total_seconds() / 86400)

    recency = max(0.0, 1.0 - days_since_push / 730.0)

    # Star velocity (stars per month)
    stars = repo.get("stars", 0) or 0
    fetched_at = repo.get("fetched_at")
    if fetched_at is not None:
        if isinstance(fetched_at, str):
            try:
                fetched_at = datetime.fromisoformat(
                    fetched_at.replace("Z", "+00:00")
                )
            except ValueError:
                fetched_at = None

    # Approximate repo age: use last_pushed_at as upper bound, or fetched_at
    # We don't have a creation date in the normalized schema, so approximate
    # from last_pushed_at back 1 year if we don't have better info
    repo_age_days = 365  # default assumption
    if last_pushed and isinstance(last_pushed, datetime):
        # Rough heuristic: repo is at least as old as stars suggest
        repo_age_days = max(30, days_since_push + 30)

    star_vel = stars / max(1.0, repo_age_days / 30.0)
    star_score = math.log10(1.0 + min(star_vel, 1000.0)) / math.log10(1001.0)

    # Issue signal
    open_issues = repo.get("open_issues", 0) or 0
    issue_sig = min(1.0, open_issues / 50.0)

    s_activity = 0.50 * recency + 0.35 * star_score + 0.15 * issue_sig
    return round(min(1.0, max(0.0, s_activity)), 6)
