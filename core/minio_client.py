from minio import Minio
from core.config import settings

minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE
)

def init_minio():
    buckets = [
        settings.MINIO_BUCKET_PRODUCT_IMAGES,
        settings.MINIO_BUCKET_REVIEW_IMAGES,
        settings.MINIO_BUCKET_REVIEW_VIDEOS
    ]
    for bucket in buckets:
        if not minio_client.bucket_exists(bucket):
            minio_client.make_bucket(bucket)
            # Set public read policy for the bucket if needed
            # For now, we assume simple public read for these assets
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
