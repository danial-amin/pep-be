"""
Storage abstraction for document uploads.

Supports:
- local: Railway Volume or local filesystem (UPLOAD_DIR)
- s3: Railway Storage Buckets (S3-compatible)
"""
import io
import tempfile
from pathlib import Path
from typing import BinaryIO, Optional

from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# S3 prefix for object keys - distinguishes from local paths
S3_KEY_PREFIX = "documents/"


def _get_s3_client():
    """Lazy init S3 client for Railway Storage Buckets."""
    import boto3
    from botocore.config import Config

    if not all([
        settings.S3_ACCESS_KEY_ID,
        settings.S3_SECRET_ACCESS_KEY,
        settings.S3_BUCKET,
        settings.S3_ENDPOINT,
    ]):
        raise ValueError(
            "S3 storage requires S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_BUCKET, S3_ENDPOINT"
        )
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        region_name=settings.S3_REGION or "auto",
        config=Config(signature_version="s3v4"),
    )


async def store_file(
    content: bytes,
    object_key: str,
) -> str:
    """
    Store file content. Returns storage location (path or S3 key).

    - local: writes to UPLOAD_DIR, returns absolute path
    - s3: uploads to bucket, returns S3 key (with prefix)
    """
    if settings.STORAGE_TYPE == "s3":
        key = f"{S3_KEY_PREFIX}{object_key}"
        client = _get_s3_client()
        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=content,
            ContentType="application/octet-stream",
        )
        logger.info("Stored file in S3: %s", key)
        return key

    # local storage
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = (upload_dir / object_key).resolve()
    with open(file_path, "wb") as f:
        f.write(content)
    logger.info("Stored file locally: %s", file_path)
    return str(file_path)


async def fetch_file_content(storage_location: str) -> bytes:
    """
    Fetch file content from storage.

    - If storage_location starts with S3_KEY_PREFIX: fetch from S3
    - Else: read from local path
    """
    if storage_location.startswith(S3_KEY_PREFIX):
        client = _get_s3_client()
        response = client.get_object(
            Bucket=settings.S3_BUCKET,
            Key=storage_location,
        )
        return response["Body"].read()

    # local path
    path = Path(storage_location)
    if not path.exists():
        raise FileNotFoundError(f"Stored file not found: {storage_location}")
    return path.read_bytes()


async def fetch_to_temp_file(storage_location: str, suffix: str = "") -> str:
    """
    Fetch file to a temporary file and return its path.
    Caller must delete the temp file when done.
    """
    content = await fetch_file_content(storage_location)
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with open(fd, "wb") as f:
            f.write(content)
        return path
    except Exception:
        Path(path).unlink(missing_ok=True)
        raise


async def delete_file(storage_location: str) -> None:
    """Delete file from storage."""
    if storage_location.startswith(S3_KEY_PREFIX):
        client = _get_s3_client()
        try:
            client.delete_object(
                Bucket=settings.S3_BUCKET,
                Key=storage_location,
            )
            logger.info("Deleted S3 object: %s", storage_location)
        except Exception as e:
            logger.warning("Failed to delete S3 object %s: %s", storage_location, e)
    else:
        path = Path(storage_location)
        if path.exists():
            try:
                path.unlink()
                logger.info("Deleted local file: %s", storage_location)
            except OSError as e:
                logger.warning("Failed to delete local file %s: %s", storage_location, e)
