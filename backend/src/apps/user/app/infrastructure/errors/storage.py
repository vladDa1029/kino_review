from app.domain.errors.base import ApplicationError


class StorageUploadError(ApplicationError):
    """Upload failed."""


class StorageDownloadError(ApplicationError):
    """Download failed."""


class StorageDeleteError(ApplicationError):
    """Delete failed."""


class StorageStreamError(ApplicationError):
    """Stream failed."""
