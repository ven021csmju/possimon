import os
import uuid
import io
from fastapi import UploadFile, HTTPException
from core.config import settings
from core.minio_client import minio_client

class ImageService:
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

    @staticmethod
    def validate_image(file: UploadFile):
        # Check file extension
        ext = file.filename.split(".")[-1].lower()
        if ext not in ImageService.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"File extension {ext} not allowed. Allowed: {ImageService.ALLOWED_EXTENSIONS}"
            )
        return ext

    @staticmethod
    async def upload_product_image(file: UploadFile, product_id: int):
        ext = ImageService.validate_image(file)
        
        # Read file content to check size and for MinIO upload
        content = await file.read()
        if len(content) > ImageService.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File size too large. Max 5MB.")
        
        # Generate unique filename
        filename = f"{product_id}/{uuid.uuid4()}.{ext}"
        
        # Upload to MinIO
        try:
            minio_client.put_object(
                settings.MINIO_BUCKET_PRODUCT_IMAGES,
                filename,
                io.BytesIO(content),
                length=len(content),
                content_type=file.content_type
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not save file to MinIO: {str(e)}")

        # Generate URL
        base_url = settings.MINIO_EXTERNAL_URL or f"http://{settings.MINIO_ENDPOINT}"
        image_url = f"{base_url}/{settings.MINIO_BUCKET_PRODUCT_IMAGES}/{filename}"
        
        return image_url, filename

    @staticmethod
    def delete_image_file(filename: str):
        if filename:
            try:
                minio_client.remove_object(settings.MINIO_BUCKET_PRODUCT_IMAGES, filename)
            except Exception as e:
                print(f"Error deleting file {filename} from MinIO: {e}")
