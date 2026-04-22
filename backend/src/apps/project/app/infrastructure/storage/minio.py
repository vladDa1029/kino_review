import inspect
from uuid import uuid4

import aioboto3
from botocore.exceptions import ClientError

from app.application.ports.domain import DocumentStoragePort, StoredFile
from app.config import Minio
from app.domain.errors.business import ExternalServiceError


class MinioDocumentStorage(DocumentStoragePort):
    def __init__(self, settings: Minio) -> None:
        self._settings = settings
        self._session = aioboto3.Session()
        self._bucket_checked = False

    async def upload(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        storage_key: str | None = None,
    ) -> StoredFile:
        await self._ensure_bucket()
        resolved_storage_key = storage_key or f"{uuid4()}-{filename}"
        try:
            async with self._client() as client:
                await client.put_object(
                    Bucket=self._settings.bucket,
                    Key=resolved_storage_key,
                    Body=content,
                    ContentType=content_type,
                )
        except ClientError as exc:
            raise ExternalServiceError(f"MinIO put_object failed: {exc}") from exc

        return StoredFile(
            bucket=self._settings.bucket,
            storage_key=resolved_storage_key,
            size=len(content),
            mime_type=content_type,
        )

    async def get_download_url(self, *, storage_key: str) -> str:
        await self._ensure_bucket()
        try:
            async with self._client() as client:
                result = client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": self._settings.bucket, "Key": storage_key},
                    ExpiresIn=self._settings.presign_expires_seconds,
                )
                if inspect.isawaitable(result):
                    return await result
                return result
        except ClientError as exc:
            raise ExternalServiceError(f"MinIO presign failed: {exc}") from exc

    async def ensure_bucket_ready(self) -> bool:
        return await self._ensure_bucket()

    async def _ensure_bucket(self) -> bool:
        if self._bucket_checked:
            return False
        created = False
        try:
            async with self._client() as client:
                try:
                    await client.head_bucket(Bucket=self._settings.bucket)
                except ClientError as exc:
                    if not _is_missing_bucket_error(exc):
                        raise
                    try:
                        await client.create_bucket(**_create_bucket_kwargs(self._settings))
                        created = True
                    except ClientError as create_exc:
                        if not _is_existing_bucket_error(create_exc):
                            raise
        except ClientError as exc:
            raise ExternalServiceError(f"MinIO bucket check/create failed: {exc}") from exc
        self._bucket_checked = True
        return created

    def _client(self):
        return self._session.client(
            "s3",
            endpoint_url=self._settings.endpoint_url,
            aws_access_key_id=self._settings.access_key,
            aws_secret_access_key=self._settings.secret_key,
            region_name=self._settings.region_name,
            use_ssl=self._settings.secure,
        )


async def ensure_minio_bucket(settings: Minio) -> bool:
    storage = MinioDocumentStorage(settings)
    return await storage.ensure_bucket_ready()


def _create_bucket_kwargs(settings: Minio) -> dict[str, object]:
    kwargs: dict[str, object] = {"Bucket": settings.bucket}
    if settings.region_name != "us-east-1":
        kwargs["CreateBucketConfiguration"] = {
            "LocationConstraint": settings.region_name,
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
