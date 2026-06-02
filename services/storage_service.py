import uuid
from fastapi import UploadFile, HTTPException
from supabase import create_client, Client
from core.config import settings

class StorageService:
    _client: Client = None
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_VIDEO_SIZE = 70 * 1024 * 1024 # 70MB

    @classmethod
    def get_client(cls) -> Client:
        if cls._client is None:
            # For debugging purposes, but never log the actual key!
            from core.config import settings
            import logging
            logger = logging.getLogger(__name__)
            
            if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
                logger.error(f"Supabase configuration missing: URL={'set' if settings.SUPABASE_URL else 'missing'}, Key={'set' if settings.SUPABASE_SERVICE_ROLE_KEY else 'missing'}")
                raise RuntimeError("Supabase credentials not configured")
            
            cls._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        return cls._client

    @staticmethod
    async def upload_file(bucket: str, file: UploadFile) -> str:
        client = StorageService.get_client()
        content = await file.read()
        
        # Reset file pointer for potential future reads (though we already read it)
        await file.seek(0)

        ext = file.filename.split(".")[-1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        
        try:
            # Upload to Supabase Storage
            res = client.storage.from_(bucket).upload(
                path=filename,
                file=content,
                file_options={"content-type": file.content_type}
            )
            
            # Get Public URL
            public_url = client.storage.from_(bucket).get_public_url(filename)
            return public_url
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not upload file to Supabase: {str(e)}")

    @staticmethod
    async def upload_image(file: UploadFile) -> str:
        # Simple validation
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        content = await file.read()
        await file.seek(0)
        if len(content) > StorageService.MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail=f"Image too large. Max {StorageService.MAX_IMAGE_SIZE//(1024*1024)}MB")
            
        return await StorageService.upload_file(settings.SUPABASE_BUCKET_IMAGES, file)

    @staticmethod
    async def upload_video(file: UploadFile) -> str:
        # Simple validation
        if not file.content_type.startswith("video/"):
            raise HTTPException(status_code=400, detail="File must be a video")
        
        content = await file.read()
        await file.seek(0)
        if len(content) > StorageService.MAX_VIDEO_SIZE:
            raise HTTPException(status_code=400, detail=f"Video too large. Max {StorageService.MAX_VIDEO_SIZE//(1024*1024)}MB")
            
        return await StorageService.upload_file(settings.SUPABASE_BUCKET_VIDEOS, file)

    @staticmethod
    async def upload_product_image(file: UploadFile, product_id: int) -> tuple[str, str]:
        client = StorageService.get_client()
        content = await file.read()
        await file.seek(0)
        
        ext = file.filename.split(".")[-1].lower()
        filename = f"{product_id}/{uuid.uuid4()}.{ext}"
        
        try:
            client.storage.from_(settings.SUPABASE_BUCKET_PRODUCT_IMAGES).upload(
                path=filename,
                file=content,
                file_options={"content-type": file.content_type}
            )
            url = client.storage.from_(settings.SUPABASE_BUCKET_PRODUCT_IMAGES).get_public_url(filename)
            return url, filename
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not upload product image to Supabase: {str(e)}")

    @staticmethod
    async def delete_file(bucket: str, filename: str):
        try:
            client = StorageService.get_client()
            client.storage.from_(bucket).remove([filename])
        except Exception as e:
            print(f"Error deleting file {filename} from Supabase bucket {bucket}: {e}")
