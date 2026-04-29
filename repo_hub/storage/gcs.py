"""GCS delta sync with ETag-based deduplication."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any


def _md5_file(path: Path) -> str:
    """Compute MD5 of a local file."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class GCSStore:
    """Google Cloud Storage store with ETag-based delta sync."""

    def __init__(self, bucket: str, prefix: str) -> None:
        self.bucket_name = bucket
        self.prefix = prefix.rstrip("/") + "/" if prefix else ""
        self._client: Any = None
        self._bucket: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from google.cloud import storage  # type: ignore

                self._client = storage.Client()
                self._bucket = self._client.bucket(self.bucket_name)
            except ImportError:
                raise ImportError("google-cloud-storage is required for GCS access")
        return self._client

    def _get_bucket(self) -> Any:
        self._get_client()
        return self._bucket

    def _full_key(self, gcs_key: str) -> str:
        if gcs_key.startswith(self.prefix):
            return gcs_key
        return self.prefix + gcs_key

    def restore(self, local_dir: Path) -> int:
        """Download all blobs under prefix to local_dir. Returns count downloaded."""
        bucket = self._get_bucket()
        local_dir = Path(local_dir)
        count = 0

        blobs = list(bucket.list_blobs(prefix=self.prefix))
        for blob in blobs:
            # Compute relative path from prefix
            rel = blob.name[len(self.prefix):]
            if not rel:
                continue
            local_path = local_dir / rel

            # Check if local file is already up-to-date via ETag
            if local_path.exists():
                local_md5 = _md5_file(local_path)
                # GCS ETag for simple objects is the MD5 hex digest
                gcs_etag = blob.etag.strip('"') if blob.etag else ""
                if local_md5 == gcs_etag:
                    continue

            local_path.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(local_path))
            count += 1

        return count

    def push_file(self, local_path: Path, gcs_key: str) -> bool:
        """Upload a single file. Returns True if actually uploaded (not skipped)."""
        bucket = self._get_bucket()
        full_key = self._full_key(gcs_key)
        blob = bucket.blob(full_key)

        # ETag dedup: check if remote already has same MD5
        try:
            blob.reload()
            gcs_etag = blob.etag.strip('"') if blob.etag else ""
            local_md5 = _md5_file(local_path)
            if local_md5 == gcs_etag:
                return False
        except Exception:
            pass  # Blob doesn't exist yet or reload failed

        blob.upload_from_filename(str(local_path))
        return True

    def push_dir(self, local_dir: Path, gcs_prefix: str) -> int:
        """Upload all files in local_dir recursively. Returns count uploaded."""
        local_dir = Path(local_dir)
        count = 0
        for path in local_dir.rglob("*"):
            if path.is_file():
                rel = path.relative_to(local_dir)
                gcs_key = gcs_prefix.rstrip("/") + "/" + str(rel)
                if self.push_file(path, gcs_key):
                    count += 1
        return count

    def list_blobs(self, prefix: str) -> list[str]:
        """List all blob names under a prefix."""
        bucket = self._get_bucket()
        full_prefix = self._full_key(prefix)
        return [blob.name for blob in bucket.list_blobs(prefix=full_prefix)]

    def download(self, gcs_key: str, local_path: Path) -> None:
        """Download a single blob to a local path."""
        bucket = self._get_bucket()
        full_key = self._full_key(gcs_key)
        blob = bucket.blob(full_key)
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(local_path))

    def upload(
        self,
        local_path: Path,
        gcs_key: str,
        metadata: dict | None = None,
    ) -> None:
        """Upload a single blob with optional metadata."""
        bucket = self._get_bucket()
        full_key = self._full_key(gcs_key)
        blob = bucket.blob(full_key)
        if metadata:
            blob.metadata = metadata
        blob.upload_from_filename(str(local_path))
