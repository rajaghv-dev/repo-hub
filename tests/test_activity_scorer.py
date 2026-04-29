"""Tests for activity_scorer.score_activity."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from repo_hub.scorer.activity_scorer import score_activity


def test_archived_repo_returns_zero():
    """Archived repo → 0.0."""
    repo = {
        "is_archived": True,
        "stars": 5000,
        "open_issues": 10,
        "last_pushed_at": datetime.now(timezone.utc),
    }
    assert score_activity(repo) == 0.0


def test_recent_high_star_repo():
    """Repo pushed today, many stars → > 0.7."""
    repo = {
        "is_archived": False,
        "stars": 10000,
        "open_issues": 50,
        "last_pushed_at": datetime.now(timezone.utc),
    }
    score = score_activity(repo)
    assert score > 0.7, f"Expected score > 0.7 for high-star recent repo, got {score}"


def test_stale_repo_low_score():
    """Repo pushed 2 years ago → < 0.3."""
    repo = {
        "is_archived": False,
        "stars": 50,
        "open_issues": 2,
        "last_pushed_at": datetime.now(timezone.utc) - timedelta(days=730),
    }
    score = score_activity(repo)
    assert score < 0.3, f"Expected score < 0.3 for stale repo, got {score}"


def test_score_in_range():
    """Score should always be in [0, 1]."""
    repos = [
        {
            "is_archived": False,
            "stars": s,
            "open_issues": i,
            "last_pushed_at": datetime.now(timezone.utc) - timedelta(days=d),
        }
        for s, i, d in [(0, 0, 1000), (100, 10, 0), (50000, 200, 0), (1, 0, 500)]
    ]
    for repo in repos:
        score = score_activity(repo)
        assert 0.0 <= score <= 1.0, f"Score {score} out of range for repo {repo}"


def test_star_velocity_contribution():
    """Higher star velocity → higher score (all else equal)."""
    base = {
        "is_archived": False,
        "open_issues": 0,
        "last_pushed_at": datetime.now(timezone.utc),
    }
    low_star = dict(base, stars=10)
    high_star = dict(base, stars=5000)

    s_low = score_activity(low_star)
    s_high = score_activity(high_star)
    assert s_high > s_low, "Higher star count should produce higher score"


def test_issue_signal_contribution():
    """More open issues → higher issue_sig contribution."""
    base = {
        "is_archived": False,
        "stars": 100,
        "last_pushed_at": datetime.now(timezone.utc),
    }
    no_issues = dict(base, open_issues=0)
    many_issues = dict(base, open_issues=100)

    s_no = score_activity(no_issues)
    s_many = score_activity(many_issues)
    assert s_many > s_no, "More issues should produce higher score"


def test_none_last_pushed_treated_as_stale():
    """None last_pushed_at → treated as very stale."""
    repo = {
        "is_archived": False,
        "stars": 500,
        "open_issues": 10,
        "last_pushed_at": None,
    }
    score = score_activity(repo)
    assert score < 0.5, f"Expected low score for repo with no push date, got {score}"
