"""Sentence embedding using BAAI/bge-small-en-v1.5."""
from __future__ import annotations

from typing import Any


class Embedder:
    """Lazy-loading sentence embedder backed by sentence-transformers."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        batch_size: int = 256,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._model: Any = None

    def _load(self) -> Any:
        """Lazy-load the model on first use."""
        if self._model is None:
            # Lazy import to avoid slow startup for browse commands
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts. Returns list of 384-dim float vectors."""
        model = self._load()
        if not texts:
            return []
        embeddings = model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return [emb.tolist() for emb in embeddings]

    def embed_repo(self, repo: dict) -> list[float]:
        """Embed a single repo as '{name}: {description}'."""
        name = repo.get("name", "")
        description = repo.get("description", "") or ""
        text = f"{name}: {description}".strip()
        result = self.embed([text])
        return result[0] if result else []


async def embed_repos(embedder: Embedder, conn: Any, repos: list[dict]) -> int:
    """
    Embed repos not yet in repo_embeddings table.

    Returns count of newly embedded repos.
    """
    if not repos:
        return 0

    # Find which repos already have embeddings
    repo_ids = [r["id"] for r in repos]
    existing_ids: set[str] = set()

    # Query in batches to avoid huge IN clauses
    batch_size = 500
    for i in range(0, len(repo_ids), batch_size):
        batch = repo_ids[i : i + batch_size]
        placeholders = ", ".join(f"${j+1}" for j in range(len(batch)))
        sql = f"SELECT repo_id FROM repo_embeddings WHERE repo_id IN ({placeholders})"
        async with conn.cursor() as cur:
            await cur.execute(sql, batch)
            rows = await cur.fetchall()
            for row in rows:
                existing_ids.add(row[0])

    # Filter to repos that need embedding
    to_embed = [r for r in repos if r["id"] not in existing_ids]
    if not to_embed:
        return 0

    # Build texts and embed in batches
    count = 0
    for i in range(0, len(to_embed), embedder.batch_size):
        batch = to_embed[i : i + embedder.batch_size]
        texts = [
            f"{r.get('name', '')}: {r.get('description', '') or ''}".strip()
            for r in batch
        ]
        vectors = embedder.embed(texts)

        rows = [
            {
                "repo_id": batch[j]["id"],
                "embedding": "[" + ",".join(str(x) for x in vectors[j]) + "]",
                "model": embedder.model_name,
            }
            for j in range(len(batch))
            if j < len(vectors)
        ]

        if rows:
            from repo_hub.storage.db import upsert_embeddings

            await upsert_embeddings(conn, rows)
            count += len(rows)

    return count
