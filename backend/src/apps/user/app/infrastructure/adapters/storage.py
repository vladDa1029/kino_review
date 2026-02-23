from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import boto3

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
