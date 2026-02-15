from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class StoredObject:
    bucket: str
    key: str
    size: int | None = None
    content_type: str | None = None


class FileStorage(Protocol):
    async def upload(
        self,
        data: bytes,
        key: str,
        bucket: str | None = None,
        content_type: str | None = None,
    ) -> StoredObject:
        raise NotImplementedError

    async def download(self, key: str, bucket: str | None = None) -> bytes:
        raise NotImplementedError

    async def delete(self, key: str, bucket: str | None = None) -> None:
        raise NotImplementedError

    async def stream(
        self,
        key: str,
        bucket: str | None = None,
        chunk_size: int = 1024 * 1024,
    ) -> AsyncIterator[bytes]:
        raise NotImplementedError
