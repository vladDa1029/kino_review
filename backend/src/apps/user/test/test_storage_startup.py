import asyncio
from pathlib import Path

from botocore.exceptions import ClientError

from app.config import StorageSettings
from app.infrastructure.adapters.storage import prepare_file_storage


class FakeS3Client:
    def __init__(self, *, missing_bucket: bool) -> None:
        self.missing_bucket = missing_bucket
        self.head_calls: list[str] = []
        self.create_calls: list[dict[str, object]] = []

    def head_bucket(self, *, Bucket: str) -> None:
        self.head_calls.append(Bucket)
        if self.missing_bucket:
            raise ClientError(
                {
                    "Error": {"Code": "404", "Message": "Not Found"},
                    "ResponseMetadata": {"HTTPStatusCode": 404},
                },
                "HeadBucket",
            )

    def create_bucket(self, **kwargs) -> None:
        self.create_calls.append(kwargs)

    def close(self) -> None:
        return None


def test_prepare_file_storage_creates_local_bucket_directory(tmp_path: Path) -> None:
    settings = StorageSettings(
        STORAGE_BACKEND="local",
        STORAGE_BUCKET="user",
        STORAGE_LOCAL_ROOT=tmp_path,
    )

    result = asyncio.run(prepare_file_storage(settings))

    assert result.backend == "local"
    assert result.bucket_created is True
    assert result.local_path == (tmp_path / "user").resolve()
    assert result.local_path.exists()


def test_prepare_file_storage_creates_missing_s3_bucket(monkeypatch) -> None:
    fake_client = FakeS3Client(missing_bucket=True)
    monkeypatch.setattr(
        "app.infrastructure.adapters.storage.boto3.client",
        lambda *_args, **_kwargs: fake_client,
    )
    settings = StorageSettings(
        STORAGE_BACKEND="s3",
        STORAGE_BUCKET="user",
        STORAGE_S3_ENDPOINT="http://minio:9000",
        STORAGE_S3_REGION="us-east-1",
        STORAGE_S3_ACCESS_KEY="minio",
        STORAGE_S3_SECRET_KEY="secret",
        STORAGE_S3_USE_SSL=False,
    )

    result = asyncio.run(prepare_file_storage(settings))

    assert result.backend == "s3"
    assert result.bucket_created is True
    assert fake_client.head_calls == ["user"]
    assert fake_client.create_calls == [{"Bucket": "user"}]
