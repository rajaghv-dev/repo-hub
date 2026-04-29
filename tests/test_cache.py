"""Tests for Cache class."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest


def test_get_returns_none_for_missing(tmp_cache):
    """get() returns None for an org not in cache."""
    result = tmp_cache.get("nonexistent-org")
    assert result is None


def test_put_and_get_roundtrip(tmp_cache):
    """put() then get() returns the same data."""
    data = [
        {"id": "llvm/circt", "name": "circt", "stars": 2000},
        {"id": "iree-org/iree", "name": "iree", "stars": 1000},
    ]
    tmp_cache.put("llvm", data)
    result = tmp_cache.get("llvm")
    assert result is not None
    assert len(result) == 2
    assert result[0]["id"] == "llvm/circt"


def test_get_returns_none_after_ttl_expiry(tmp_path):
    """get() returns None for stale cache entry."""
    from repo_hub.storage.cache import Cache

    cache = Cache(tmp_path, ttl_hours=1)
    data = [{"id": "test/repo", "stars": 100}]
    cache.put("testorg", data)

    # Manually expire by writing old timestamp
    cache_path = tmp_path / "cache" / "orgs" / "testorg.json"
    payload = json.loads(cache_path.read_text())
    old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    payload["fetched_at"] = old_time
    cache_path.write_text(json.dumps(payload))

    result = cache.get("testorg")
    assert result is None


def test_is_fresh_false_for_missing(tmp_cache):
    """is_fresh() returns False for non-existent org."""
    assert tmp_cache.is_fresh("missing") is False


def test_is_fresh_true_after_put(tmp_cache):
    """is_fresh() returns True immediately after put."""
    tmp_cache.put("myorg", [{"id": "myorg/repo"}])
    assert tmp_cache.is_fresh("myorg") is True


def test_dep_cache_roundtrip(tmp_cache):
    """put_dep() then get_dep() returns the same content."""
    content = "torch\nnumpy\n"
    tmp_cache.put_dep("pytorch", "pytorch", "requirements.txt", content)
    result = tmp_cache.get_dep("pytorch", "pytorch", "requirements.txt")
    assert result == content


def test_dep_cache_missing_returns_none(tmp_cache):
    """get_dep() returns None for a missing dep file."""
    result = tmp_cache.get_dep("org", "repo", "requirements.txt")
    assert result is None


def test_dep_is_fresh_false_for_missing(tmp_cache):
    """is_dep_fresh() returns False for missing dep."""
    assert tmp_cache.is_dep_fresh("org", "repo", "file.txt") is False


def test_dep_is_fresh_true_after_put(tmp_cache):
    """is_dep_fresh() returns True after putting a dep."""
    tmp_cache.put_dep("org", "repo", "Cargo.toml", "[dependencies]\n")
    assert tmp_cache.is_dep_fresh("org", "repo", "Cargo.toml") is True


def test_stats_returns_dict(tmp_cache):
    """stats() returns a dict with count and total_size."""
    tmp_cache.put("org1", [{"id": "org1/r1"}])
    tmp_cache.put("org2", [{"id": "org2/r1"}, {"id": "org2/r2"}])
    stats = tmp_cache.stats()
    assert isinstance(stats, dict)
    assert "count" in stats
    assert "total_size" in stats
    assert stats["count"] >= 2
    assert stats["total_size"] > 0
