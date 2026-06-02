import os
import uuid
import io
from fastapi import UploadFile, HTTPException
from core.config import settings
from services.storage_service import StorageService

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
        
        # Check size (Supabase handles this too but we can keep it for early failure)
        content = await file.read()
        await file.seek(0)
        if len(content) > ImageService.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File size too large. Max 5MB.")
        
        # Upload to Supabase
        image_url, file_path = await StorageService.upload_product_image(file, product_id)
        
        return image_url, file_path

    @staticmethod
    def delete_image_file(filename: str):
        if filename:
            import asyncio
            # filename is expected to be "product_id/uuid.ext"
            asyncio.create_task(StorageService.delete_file(settings.SUPABASE_BUCKET_PRODUCT_IMAGES, filename))
