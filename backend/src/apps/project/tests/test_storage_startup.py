import asyncio

from botocore.exceptions import ClientError

from app.config import Minio
from app.infrastructure.storage.minio import ensure_minio_bucket


class FakeMinioClient:
    def __init__(self, *, missing_bucket: bool) -> None:
        self.missing_bucket = missing_bucket
        self.head_calls: list[str] = []
        self.create_calls: list[dict[str, object]] = []

    async def head_bucket(self, *, Bucket: str) -> None:
        self.head_calls.append(Bucket)
        if self.missing_bucket:
            raise ClientError(
                {
                    "Error": {"Code": "404", "Message": "Not Found"},
                    "ResponseMetadata": {"HTTPStatusCode": 404},
                },
                "HeadBucket",
            )

    async def create_bucket(self, **kwargs) -> None:
        self.create_calls.append(kwargs)


class FakeMinioClientContext:
    def __init__(self, client: FakeMinioClient) -> None:
        self._client = client

    async def __aenter__(self) -> FakeMinioClient:
        return self._client

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class FakeSession:
    def __init__(self, client: FakeMinioClient) -> None:
        self._client = client

    def client(self, *_args, **_kwargs) -> FakeMinioClientContext:
        return FakeMinioClientContext(self._client)


def test_ensure_minio_bucket_creates_missing_bucket(monkeypatch) -> None:
    fake_client = FakeMinioClient(missing_bucket=True)
    monkeypatch.setattr(
        "app.infrastructure.storage.minio.aioboto3.Session",
        lambda: FakeSession(fake_client),
    )
    settings = Minio(
        MINIO_ENDPOINT_URL="http://minio:9000",
        MINIO_ACCESS_KEY="minio",
        MINIO_SECRET_KEY="secret",
        MINIO_BUCKET="project-documents",
    )

    created = asyncio.run(ensure_minio_bucket(settings))

    assert created is True
    assert fake_client.head_calls == ["project-documents"]
    assert fake_client.create_calls == [{"Bucket": "project-documents"}]


def test_ensure_minio_bucket_keeps_existing_bucket(monkeypatch) -> None:
    fake_client = FakeMinioClient(missing_bucket=False)
    monkeypatch.setattr(
        "app.infrastructure.storage.minio.aioboto3.Session",
        lambda: FakeSession(fake_client),
    )
    settings = Minio(
        MINIO_ENDPOINT_URL="http://minio:9000",
        MINIO_ACCESS_KEY="minio",
        MINIO_SECRET_KEY="secret",
        MINIO_BUCKET="project-documents",
    )

    created = asyncio.run(ensure_minio_bucket(settings))

    assert created is False
    assert fake_client.head_calls == ["project-documents"]
    assert fake_client.create_calls == []
