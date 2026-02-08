"""
MinIO (S3-compatible) utilities: upload, delete, get file stream.
Uses boto3 with endpoint_url for MinIO.
"""
import uuid
from typing import BinaryIO, List, Optional, Tuple

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import settings


def _get_client():
    """Build S3-compatible client for MinIO."""
    endpoint = (settings.MINIO_SERVER_URL or "").strip().rstrip("/")
    if not endpoint:
        raise ValueError("MINIO_SERVER_URL is not set")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=(settings.MINIO_ROOT_USER or "").strip(),
        aws_secret_access_key=(settings.MINIO_ROOT_PASSWORD or "").strip(),
        config=BotoConfig(signature_version="s3v4"),
        region_name="us-east-1",
    )


def _bucket():
    return (settings.MINIO_BUCKET_NAME).strip()


def ensure_bucket_exists():
    """Create bucket if it does not exist."""
    client = _get_client()
    bucket = _bucket()
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            client.create_bucket(Bucket=bucket)
        else:
            raise


def upload_file(file_content: BinaryIO, content_type: str, key: Optional[str] = None) -> str:
    """
    Upload a file to MinIO. Returns the object key (filename) to store in DB.
    If key is None, generates a unique key.
    """
    ensure_bucket_exists()
    client = _get_client()
    if key is None:
        ext = "bin"
        if content_type and "image/" in content_type:
            ext = (content_type.split("/")[-1].split(";")[0].strip() or "bin")
        key = f"products/{uuid.uuid4().hex}.{ext}"
    body = file_content.read() if hasattr(file_content, "read") else file_content
    client.put_object(
        Bucket=_bucket(),
        Key=key,
        Body=body,
        ContentType=content_type or "application/octet-stream",
    )
    return key


def delete_file(key: str) -> bool:
    """Delete one object from MinIO. Returns True if deleted or not found."""
    client = _get_client()
    try:
        client.delete_object(Bucket=_bucket(), Key=key)
        return True
    except ClientError:
        return False


def delete_files(keys: List[str]) -> None:
    """Delete multiple objects. Ignores errors for missing keys."""
    if not keys:
        return
    client = _get_client()
    for key in keys:
        try:
            client.delete_object(Bucket=_bucket(), Key=key)
        except ClientError:
            pass


def get_file_stream(key: str) -> Tuple[Optional[BinaryIO], Optional[str]]:
    """
    Get object from MinIO as (stream, content_type).
    Returns (None, None) if not found.
    """
    client = _get_client()
    try:
        resp = client.get_object(Bucket=_bucket(), Key=key)
        stream = resp["Body"]
        content_type = resp.get("ContentType") or "application/octet-stream"
        return stream, content_type
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return None, None
        raise
