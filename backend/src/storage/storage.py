import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
DEFAULT_BUCKET = os.getenv("S3_BUCKET_NAME", "your-bucket-name")


def get_s3_client():
    """
    Returns a boto3 S3 client.
    Credentials are pulled from environment variables automatically.
    If running on EC2/Lambda with an IAM role, no credentials are needed.
    """
    return boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,  # None → boto3 uses IAM role
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )


# ── Upload helpers ──────────────────────────────────────────────────────────────


def upload_file(
    local_path: str, s3_key: str = None, bucket: str = DEFAULT_BUCKET
) -> str:
    """
    Upload a single local file to S3.

    Args:
        local_path : Path to the local file, e.g. "/tmp/report.pdf"
        s3_key     : Destination key in S3, e.g. "reports/2024/report.pdf"
                     Defaults to the file's basename.
        bucket     : Target S3 bucket. Defaults to DEFAULT_BUCKET.

    Returns:
        The S3 URI of the uploaded file: s3://bucket/key
    """
    if s3_key is None:
        s3_key = Path(local_path).name  # e.g. "report.pdf"

    client = get_s3_client()
    try:
        client.upload_file(local_path, bucket, s3_key)
        uri = f"s3://{bucket}/{s3_key}"
        print(f"✅ Uploaded: {local_path}  →  {uri}")
        return uri
    except FileNotFoundError:
        raise FileNotFoundError(f"Local file not found: {local_path}")
    except NoCredentialsError:
        raise EnvironmentError(
            "AWS credentials not found. Set env vars or configure IAM role."
        )
    except ClientError as e:
        raise RuntimeError(f"S3 upload failed: {e.response['Error']['Message']}")


def upload_bytes(
    data: bytes,
    s3_key: str,
    bucket: str = DEFAULT_BUCKET,
    content_type: str = "application/octet-stream",
) -> str:
    """
    Upload raw bytes (e.g. an in-memory file) directly to S3.

    Args:
        data         : File content as bytes.
        s3_key       : Destination key in S3.
        bucket       : Target S3 bucket.
        content_type : MIME type, e.g. "image/png", "text/csv".

    Returns:
        The S3 URI of the uploaded object.
    """
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=data,
            ContentType=content_type,
        )
        uri = f"s3://{bucket}/{s3_key}"
        print(f"✅ Uploaded bytes  →  {uri}")
        return uri
    except ClientError as e:
        raise RuntimeError(f"S3 upload failed: {e.response['Error']['Message']}")


def upload_folder(
    local_folder: str, s3_prefix: str = "", bucket: str = DEFAULT_BUCKET
) -> list[str]:
    """
    Recursively upload all files in a local folder to S3.

    Args:
        local_folder : Path to the local directory.
        s3_prefix    : Prefix (subfolder) inside the bucket, e.g. "uploads/2024/".
        bucket       : Target S3 bucket.

    Returns:
        List of S3 URIs that were uploaded.
    """
    uris = []
    folder = Path(local_folder)
    for file_path in folder.rglob("*"):
        if file_path.is_file():
            relative = file_path.relative_to(folder)
            s3_key = (
                f"{s3_prefix}/{relative}".lstrip("/") if s3_prefix else str(relative)
            )
            uri = upload_file(str(file_path), s3_key, bucket)
            uris.append(uri)
    return uris


# ── Bonus: Download helper ──────────────────────────────────────────────────────


def download_file(s3_key: str, local_path: str, bucket: str = DEFAULT_BUCKET) -> str:
    """
    Download a file from S3 to a local path.

    Args:
        s3_key     : Key of the file in S3, e.g. "reports/report.pdf"
        local_path : Where to save it locally, e.g. "/tmp/report.pdf"
        bucket     : Source S3 bucket.

    Returns:
        The local path where the file was saved.
    """
    client = get_s3_client()
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    try:
        client.download_file(bucket, s3_key, local_path)
        print(f"✅ Downloaded: s3://{bucket}/{s3_key}  →  {local_path}")
        return local_path
    except ClientError as e:
        raise RuntimeError(f"S3 download failed: {e.response['Error']['Message']}")


# ── Quick test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # --- upload a file ---
    upload_file("./hello.txt", "test/hello.txt")

    # --- upload raw bytes ---
    upload_bytes(b"hello world", "test/hello1.txt", content_type="text/plain")

    # --- download a file ---
    download_file("test/hello.txt", "/tmp/hello.txt")

    print("S3 client ready. Uncomment a function above to test.")
