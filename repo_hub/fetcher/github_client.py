"""Rate-limited async GitHub REST API client."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import httpx


class GitHubClient:
    """Async GitHub API client with rate-limit awareness and backoff."""

    BASE_URL = "https://api.github.com"
    RAW_BASE = "https://raw.githubusercontent.com"

    def __init__(self, token: str) -> None:
        self.token = token
        self._remaining = 5000
        self._reset_at = datetime.now(timezone.utc)
        self._client = httpx.AsyncClient(
            http2=True,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    async def _request(
        self, url: str, params: dict | None = None, attempt: int = 0
    ) -> Any:
        """Make a single GET request, handling rate limits and retries."""
        # Sleep if rate limit is nearly exhausted
        if self._remaining < 50:
            now = datetime.now(timezone.utc)
            wait = (self._reset_at - now).total_seconds()
            if wait > 0:
                await asyncio.sleep(wait + 1)

        try:
            resp = await self._client.get(url, params=params)
        except httpx.HTTPError as e:
            if attempt < 3:
                await asyncio.sleep(2**attempt)
                return await self._request(url, params, attempt + 1)
            raise

        # Update rate limit state
        if "X-RateLimit-Remaining" in resp.headers:
            self._remaining = int(resp.headers["X-RateLimit-Remaining"])
        if "X-RateLimit-Reset" in resp.headers:
            self._reset_at = datetime.fromtimestamp(
                int(resp.headers["X-RateLimit-Reset"]), tz=timezone.utc
            )

        if resp.status_code == 429:
            # Secondary rate limit
            retry_after = int(resp.headers.get("Retry-After", 60))
            await asyncio.sleep(retry_after)
            return await self._request(url, params, attempt)

        if resp.status_code in (500, 502, 503, 504):
            if attempt < 3:
                wait = 2 ** (attempt + 1)
                await asyncio.sleep(wait)
                return await self._request(url, params, attempt + 1)
            resp.raise_for_status()

        if resp.status_code == 404:
            return None

        resp.raise_for_status()
        return resp.json()

    async def get(self, url: str, params: dict | None = None) -> Any:
        """GET a single URL, return parsed JSON."""
        if not url.startswith("http"):
            url = self.BASE_URL + url
        return await self._request(url, params)

    async def paginate(
        self, url: str, params: dict | None = None
    ) -> AsyncIterator[dict]:
        """Paginate through all pages, yielding individual items."""
        if not url.startswith("http"):
            url = self.BASE_URL + url
        params = dict(params or {})
        params.setdefault("per_page", 100)

        while url:
            if self._remaining < 50:
                now = datetime.now(timezone.utc)
                wait = (self._reset_at - now).total_seconds()
                if wait > 0:
                    await asyncio.sleep(wait + 1)

            try:
                resp = await self._client.get(url, params=params)
            except httpx.HTTPError:
                break

            if "X-RateLimit-Remaining" in resp.headers:
                self._remaining = int(resp.headers["X-RateLimit-Remaining"])
            if "X-RateLimit-Reset" in resp.headers:
                self._reset_at = datetime.fromtimestamp(
                    int(resp.headers["X-RateLimit-Reset"]), tz=timezone.utc
                )

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 60))
                await asyncio.sleep(retry_after)
                continue

            if resp.status_code in (500, 502, 503, 504):
                await asyncio.sleep(5)
                break

            if resp.status_code not in (200, 206):
                break

            data = resp.json()
            items = data if isinstance(data, list) else data.get("items", [data])
            for item in items:
                yield item

            # Follow Link header pagination
            link_header = resp.headers.get("Link", "")
            next_url = None
            for part in link_header.split(","):
                part = part.strip()
                if 'rel="next"' in part:
                    next_url = part.split(";")[0].strip().strip("<>")
                    break

            url = next_url  # type: ignore
            params = {}  # Params are embedded in next_url

    async def get_file(self, org: str, repo: str, path: str) -> str | None:
        """Fetch raw file content from GitHub."""
        url = f"{self.RAW_BASE}/{org}/{repo}/HEAD/{path}"
        try:
            resp = await self._client.get(url)
            if resp.status_code == 200:
                return resp.text
            return None
        except httpx.HTTPError:
            return None

    @property
    def rate_limit_remaining(self) -> int:
        return self._remaining

    @property
    def rate_limit_reset(self) -> datetime:
        return self._reset_at

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "GitHubClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()
