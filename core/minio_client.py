from minio import Minio
from core.config import settings

minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE
)

def init_minio():
    endpoint_hint = (
        "Use MINIO_ENDPOINT=localhost:9000 when FastAPI runs on the host. "
        "Use MINIO_ENDPOINT=minio:9000 when FastAPI runs in the same Docker Compose network as the minio service."
    )
    buckets = [
        settings.MINIO_BUCKET_PRODUCT_IMAGES,
        settings.MINIO_BUCKET_REVIEW_IMAGES,
        settings.MINIO_BUCKET_REVIEW_VIDEOS
    ]
    try:
        for bucket in buckets:
            if not minio_client.bucket_exists(bucket):
                minio_client.make_bucket(bucket)
                import json
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                            "Resource": [f"arn:aws:s3:::{bucket}"]
                        },
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{bucket}/*"]
                        }
                    ]
                }
                minio_client.set_bucket_policy(bucket, json.dumps(policy))
    except Exception as e:
        raise RuntimeError(
            f"Could not initialize MinIO at {settings.MINIO_ENDPOINT}. {endpoint_hint} Original error: {e}"
        ) from e
