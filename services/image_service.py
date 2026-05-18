import os
import uuid
from fastapi import UploadFile, HTTPException
from core.config import settings
import shutil

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
        
        # We can't easily check size without reading the file in FastAPI if it's SpooledTemporaryFile
        # But we can check after reading or use a middleware for global limit.
        # For now, we'll check after reading.
        return ext

    @staticmethod
    async def upload_product_image(file: UploadFile, product_id: int):
        ext = ImageService.validate_image(file)
        
        # Create directory if not exists
        upload_path = os.path.join(settings.UPLOAD_DIR, settings.PRODUCTS_IMAGE_DIR, str(product_id))
        os.makedirs(upload_path, exist_ok=True)
        
        # Generate unique filename
        filename = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(upload_path, filename)
        
        # Save file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
            
        # Check file size after saving (optional, but safer to check before if possible)
        if os.path.getsize(file_path) > ImageService.MAX_FILE_SIZE:
            os.remove(file_path)
            raise HTTPException(status_code=400, detail="File size too large. Max 5MB.")

        # Relative path for DB and URL generation
        relative_path = os.path.join(settings.PRODUCTS_IMAGE_DIR, str(product_id), filename).replace("\\", "/")
        image_url = f"{settings.STATIC_URL_PREFIX}/{relative_path}"
        
        return image_url, file_path

    @staticmethod
    def delete_image_file(file_path: str):
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                
                # Try to remove empty parent directory
                parent_dir = os.path.dirname(file_path)
                if not os.listdir(parent_dir):
                    os.rmdir(parent_dir)
            except Exception as e:
                # Log error but don't necessarily fail the API if DB record is gone
                print(f"Error deleting file {file_path}: {e}")
