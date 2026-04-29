"""Local JSON file cache with TTL support."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class Cache:
    """File-backed cache for org repo listings and dependency files."""

    def __init__(self, data_dir: Path, ttl_hours: int = 24) -> None:
        self.data_dir = Path(data_dir)
        self.ttl_hours = ttl_hours
        self._orgs_dir = self.data_dir / "cache" / "orgs"
        self._deps_dir = self.data_dir / "cache" / "deps"
        self._orgs_dir.mkdir(parents=True, exist_ok=True)
        self._deps_dir.mkdir(parents=True, exist_ok=True)

    # ── Org repo cache ────────────────────────────────────────────────────────

    def _org_path(self, org: str) -> Path:
        return self._orgs_dir / f"{org}.json"

    def _is_fresh(self, path: Path) -> bool:
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text())
            fetched_at_str = data.get("fetched_at", "")
            if not fetched_at_str:
                return False
            fetched_at = datetime.fromisoformat(fetched_at_str)
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - fetched_at
            return age < timedelta(hours=self.ttl_hours)
        except Exception:
            return False

    def get(self, org: str) -> list[dict] | None:
        """Return cached data or None if missing/stale."""
        path = self._org_path(org)
        if not self._is_fresh(path):
            return None
        try:
            data = json.loads(path.read_text())
            return data.get("data", [])
        except Exception:
            return None

    def put(self, org: str, data: list[dict]) -> None:
        """Write org data to cache."""
        path = self._org_path(org)
        payload = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        path.write_text(json.dumps(payload, default=str))

    def is_fresh(self, org: str) -> bool:
        return self._is_fresh(self._org_path(org))

    # ── Dep file cache ────────────────────────────────────────────────────────

    def _dep_path(self, org: str, repo: str, filename: str) -> Path:
        # Sanitize filename for filesystem
        safe_filename = filename.replace("/", "_")
        return self._deps_dir / org / repo / safe_filename

    def get_dep(self, org: str, repo: str, filename: str) -> str | None:
        """Return dep file content or None if missing/stale."""
        path = self._dep_path(org, repo, filename)
        if not self._is_fresh(path):
            return None
        try:
            data = json.loads(path.read_text())
            return data.get("data")
        except Exception:
            return None

    def put_dep(self, org: str, repo: str, filename: str, content: str) -> None:
        """Cache a dep file's content."""
        path = self._dep_path(org, repo, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "data": content,
        }
        path.write_text(json.dumps(payload))

    def is_dep_fresh(self, org: str, repo: str, filename: str) -> bool:
        return self._is_fresh(self._dep_path(org, repo, filename))

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Return cache statistics."""
        count = 0
        total_size = 0
        oldest: datetime | None = None

        for path in self._orgs_dir.glob("*.json"):
            count += 1
            total_size += path.stat().st_size
            try:
                data = json.loads(path.read_text())
                fetched_str = data.get("fetched_at", "")
                if fetched_str:
                    fetched = datetime.fromisoformat(fetched_str)
                    if fetched.tzinfo is None:
                        fetched = fetched.replace(tzinfo=timezone.utc)
                    if oldest is None or fetched < oldest:
                        oldest = fetched
            except Exception:
                pass

        for path in self._deps_dir.rglob("*"):
            if path.is_file():
                count += 1
                total_size += path.stat().st_size

        return {
            "count": count,
            "total_size": total_size,
            "oldest": oldest.isoformat() if oldest else None,
        }
