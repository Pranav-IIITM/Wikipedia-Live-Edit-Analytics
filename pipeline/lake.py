"""Lake storage: Supabase Storage (S3-compatible API or REST API), or a local folder for development.

Any S3-compatible service (AWS S3, Cloudflare R2, MinIO) works by changing the LAKE_S3_* settings.
"""

from __future__ import annotations  # `list[str]` below must not resolve to the `list` methods

import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from pipeline import config


class LocalLake:
    def __init__(self, root: Path):
        self.root = Path(root)

    def upload(self, local_path: Path, key: str) -> None:
        dest = self.root / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local_path, dest)

    def list(self, prefix: str) -> list[tuple[str, datetime]]:
        base = self.root / prefix
        if not base.exists():
            return []
        out = []
        for path in base.rglob("*"):
            if path.is_file():
                key = path.relative_to(self.root).as_posix()
                out.append((key, datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)))
        return out

    def delete(self, keys: list[str]) -> None:
        for key in keys:
            (self.root / key).unlink(missing_ok=True)

    def describe(self) -> str:
        return f"local folder {self.root}"


class S3Lake:
    def __init__(self):
        import boto3
        from botocore.config import Config

        self.bucket = config.LAKE_BUCKET
        self.client = boto3.client(
            "s3",
            endpoint_url=config.LAKE_S3_ENDPOINT,
            region_name=config.LAKE_S3_REGION,
            aws_access_key_id=config.LAKE_S3_ACCESS_KEY_ID,
            aws_secret_access_key=config.LAKE_S3_SECRET_ACCESS_KEY,
            config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 5}),
        )

    def upload(self, local_path: Path, key: str) -> None:
        self.client.upload_file(str(local_path), self.bucket, key)

    def list(self, prefix: str) -> list[tuple[str, datetime]]:
        out = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                out.append((obj["Key"], obj["LastModified"]))
        return out

    def delete(self, keys: list[str]) -> None:
        for i in range(0, len(keys), 500):
            batch = keys[i:i + 500]
            self.client.delete_objects(
                Bucket=self.bucket,
                Delete={"Objects": [{"Key": k} for k in batch], "Quiet": True},
            )

    def describe(self) -> str:
        return f"s3://{self.bucket} at {config.LAKE_S3_ENDPOINT}"


class SupabaseStorageLake:
    """Supabase Storage REST API, authenticated with the project's service role key."""

    def __init__(self):
        import requests

        self.base = config.SUPABASE_URL.rstrip("/") + "/storage/v1"
        self.bucket = config.LAKE_BUCKET
        self.session = requests.Session()
        key = config.SUPABASE_SERVICE_ROLE_KEY
        self.session.headers.update({"apikey": key, "Authorization": f"Bearer {key}"})

    def upload(self, local_path: Path, key: str) -> None:
        with open(local_path, "rb") as fh:
            resp = self.session.post(
                f"{self.base}/object/{self.bucket}/{quote(key, safe='/=')}",
                data=fh,
                headers={"Content-Type": "application/octet-stream", "x-upsert": "true"},
                timeout=120,
            )
        resp.raise_for_status()

    def _list_folder(self, prefix: str) -> list[dict]:
        items, offset = [], 0
        while True:
            resp = self.session.post(
                f"{self.base}/object/list/{self.bucket}",
                json={"prefix": prefix, "limit": 1000, "offset": offset,
                      "sortBy": {"column": "name", "order": "asc"}},
                timeout=30,
            )
            resp.raise_for_status()
            page = resp.json()
            items.extend(page)
            if len(page) < 1000:
                return items
            offset += 1000

    def list(self, prefix: str) -> list[tuple[str, datetime]]:
        """Recursive listing (the API lists one folder level at a time; folders have no id)."""
        prefix = prefix.strip("/")
        out = []
        for item in self._list_folder(prefix):
            path = f"{prefix}/{item['name']}" if prefix else item["name"]
            if item.get("id") is None:
                out.extend(self.list(path))
            else:
                stamp = item.get("updated_at") or item.get("created_at")
                out.append((path, datetime.fromisoformat(stamp.replace("Z", "+00:00")) if stamp else None))
        return out

    def delete(self, keys: list[str]) -> None:
        for i in range(0, len(keys), 500):
            resp = self.session.delete(
                f"{self.base}/object/{self.bucket}", json={"prefixes": keys[i:i + 500]}, timeout=60
            )
            resp.raise_for_status()

    def describe(self) -> str:
        return f"Supabase Storage bucket '{self.bucket}' at {config.SUPABASE_URL}"


def get_lake():
    if config.LAKE_S3_ENDPOINT:
        return S3Lake()
    if config.SUPABASE_URL and config.SUPABASE_SERVICE_ROLE_KEY:
        return SupabaseStorageLake()
    return LocalLake(config.LAKE_LOCAL_DIR)


def object_key(layer: str, day: str, run_id: str) -> str:
    """Hive-style partitioned key, e.g. bronze/date=2026-10-14/run_20261014T101500Z.parquet."""
    return f"{layer}/date={day}/run_{run_id}.parquet"


def key_date(key: str) -> str | None:
    for part in key.split("/"):
        if part.startswith("date="):
            return part[5:]
    return None
