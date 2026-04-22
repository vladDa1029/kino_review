from __future__ import annotations

import asyncio
from dataclasses import dataclass
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

from app.application.ports.storage import FileStorage, StoredObject
from app.config import StorageSettings
from app.infrastructure.constants import (
    DELETE_FILE_FAILED,
    DOWNLOAD_FILE_FAILED,
    STREAM_FILE_FAILED,
    UPLOAD_FILE_FAILED,
)
from app.infrastructure.errors.storage import (
    StorageDeleteError,
    StorageDownloadError,
    StorageStreamError,
    StorageUploadError,
)


@dataclass(frozen=True, slots=True)
class StorageStartupResult:
    backend: str
    bucket: str
    bucket_created: bool
    endpoint_url: str | None = None
    local_path: Path | None = None


class LocalFileStorage(FileStorage):
    def __init__(self, base_path: Path, default_bucket: str) -> None:
        self._base_path = base_path
        self._default_bucket = default_bucket

    def _resolve(self, key: str, bucket: str | None) -> Path:
        bucket_name = bucket or self._default_bucket
        return self._base_path / bucket_name / key

    async def upload(
        self,
        data: bytes,
        key: str,
        bucket: str | None = None,
        content_type: str | None = None,
    ) -> StoredObject:
        path = self._resolve(key, bucket)
        bucket_name = bucket or self._default_bucket
        try:
            await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(path.write_bytes, data)
        except OSError as err:
            raise StorageUploadError(UPLOAD_FILE_FAILED) from err
        return StoredObject(
            bucket=bucket_name,
            key=key,
            size=len(data),
            content_type=content_type,
        )

    async def download(self, key: str, bucket: str | None = None) -> bytes:
        path = self._resolve(key, bucket)
        try:
            return await asyncio.to_thread(path.read_bytes)
        except OSError as err:
            raise StorageDownloadError(DOWNLOAD_FILE_FAILED) from err

    async def delete(self, key: str, bucket: str | None = None) -> None:
        path = self._resolve(key, bucket)
        try:
            await asyncio.to_thread(path.unlink, missing_ok=True)
        except OSError as err:
            raise StorageDeleteError(DELETE_FILE_FAILED) from err

    async def stream(
        self,
        key: str,
        bucket: str | None = None,
        chunk_size: int = 1024 * 1024,
    ) -> AsyncIterator[bytes]:
        path = self._resolve(key, bucket)
        try:
            handle = await asyncio.to_thread(open, path, "rb")
        except OSError as err:
            raise StorageStreamError(STREAM_FILE_FAILED) from err

        try:
            while True:
                chunk = await asyncio.to_thread(handle.read, chunk_size)
                if not chunk:
                    break
                yield chunk
        except OSError as err:
            raise StorageStreamError(STREAM_FILE_FAILED) from err
        finally:
            await asyncio.to_thread(handle.close)


class S3FileStorage(FileStorage):
    def __init__(self, client: Any, default_bucket: str) -> None:
        self._client = client
        self._default_bucket = default_bucket

    async def upload(
        self,
        data: bytes,
        key: str,
        bucket: str | None = None,
        content_type: str | None = None,
    ) -> StoredObject:
        bucket_name = bucket or self._default_bucket
        kwargs = {"Bucket": bucket_name, "Key": key, "Body": data}
        if content_type is not None:
            kwargs["ContentType"] = content_type
        try:
            await asyncio.to_thread(self._client.put_object, **kwargs)
        except Exception as err:
            raise StorageUploadError(UPLOAD_FILE_FAILED) from err
        return StoredObject(
            bucket=bucket_name,
            key=key,
            size=len(data),
            content_type=content_type,
        )

    async def download(self, key: str, bucket: str | None = None) -> bytes:
        bucket_name = bucket or self._default_bucket
        try:
            response = await asyncio.to_thread(
                self._client.get_object,
                Bucket=bucket_name,
                Key=key,
            )
            return await asyncio.to_thread(response["Body"].read)
        except Exception as err:
            raise StorageDownloadError(DOWNLOAD_FILE_FAILED) from err

    async def delete(self, key: str, bucket: str | None = None) -> None:
        bucket_name = bucket or self._default_bucket
        try:
            await asyncio.to_thread(
                self._client.delete_object,
                Bucket=bucket_name,
                Key=key,
            )
        except Exception as err:
            raise StorageDeleteError(DELETE_FILE_FAILED) from err

    async def stream(
        self,
        key: str,
        bucket: str | None = None,
        chunk_size: int = 1024 * 1024,
    ) -> AsyncIterator[bytes]:
        bucket_name = bucket or self._default_bucket
        try:
            response = await asyncio.to_thread(
                self._client.get_object,
                Bucket=bucket_name,
                Key=key,
            )
            body = response["Body"]
        except Exception as err:
            raise StorageStreamError(STREAM_FILE_FAILED) from err

        try:
            while True:
                chunk = await asyncio.to_thread(body.read, chunk_size)
                if not chunk:
                    break
                yield chunk
        except Exception as err:
            raise StorageStreamError(STREAM_FILE_FAILED) from err
        finally:
            await asyncio.to_thread(body.close)


def create_file_storage(settings: StorageSettings) -> FileStorage:
    if settings.backend == "local":
        return LocalFileStorage(settings.local_root, settings.bucket)

    client_kwargs: dict[str, object] = {
        "region_name": settings.s3_region,
        "aws_access_key_id": settings.s3_access_key,
        "aws_secret_access_key": settings.s3_secret_key,
        "endpoint_url": settings.s3_endpoint_url,
        "use_ssl": settings.s3_use_ssl,
    }
    client = boto3.client(
        "s3", **{k: v for k, v in client_kwargs.items() if v is not None}
    )
    return S3FileStorage(client, settings.bucket)


async def prepare_file_storage(settings: StorageSettings) -> StorageStartupResult:
    if settings.backend == "local":
        bucket_path = (settings.local_root / settings.bucket).resolve()
        bucket_exists = bucket_path.exists()
        await asyncio.to_thread(bucket_path.mkdir, parents=True, exist_ok=True)
        return StorageStartupResult(
            backend=settings.backend,
            bucket=settings.bucket,
            bucket_created=not bucket_exists,
            local_path=bucket_path,
        )

    client_kwargs: dict[str, object] = {
        "region_name": settings.s3_region,
        "aws_access_key_id": settings.s3_access_key,
        "aws_secret_access_key": settings.s3_secret_key,
        "endpoint_url": settings.s3_endpoint_url,
        "use_ssl": settings.s3_use_ssl,
    }
    client = boto3.client(
        "s3", **{k: v for k, v in client_kwargs.items() if v is not None}
    )

    try:
        bucket_created = await _ensure_remote_bucket(client, settings)
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            await asyncio.to_thread(close)

    return StorageStartupResult(
        backend=settings.backend,
        bucket=settings.bucket,
        bucket_created=bucket_created,
        endpoint_url=settings.s3_endpoint_url,
    )


async def _ensure_remote_bucket(client: Any, settings: StorageSettings) -> bool:
    try:
        await asyncio.to_thread(client.head_bucket, Bucket=settings.bucket)
        return False
    except ClientError as exc:
        if not _is_missing_bucket_error(exc):
            raise RuntimeError(f"Storage connectivity check failed: {exc}") from exc

    try:
        await asyncio.to_thread(client.create_bucket, **_create_bucket_kwargs(settings))
        return True
    except ClientError as exc:
        if _is_existing_bucket_error(exc):
            return False
        raise RuntimeError(f"Storage bucket creation failed: {exc}") from exc


def _create_bucket_kwargs(settings: StorageSettings) -> dict[str, object]:
    kwargs: dict[str, object] = {"Bucket": settings.bucket}
    if settings.s3_region and settings.s3_region != "us-east-1":
        kwargs["CreateBucketConfiguration"] = {
            "LocationConstraint": settings.s3_region,
        }
    return kwargs


def _is_missing_bucket_error(exc: ClientError) -> bool:
    error = exc.response.get("Error", {})
    code = str(error.get("Code", ""))
    status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return code in {"404", "NoSuchBucket", "NotFound"} or status_code == 404


def _is_existing_bucket_error(exc: ClientError) -> bool:
    error = exc.response.get("Error", {})
    code = str(error.get("Code", ""))
    status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return code in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"} or status_code == 409
