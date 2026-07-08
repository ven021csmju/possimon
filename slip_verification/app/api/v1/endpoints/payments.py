from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.verification_service import VerificationService
from app.repositories.payment_repository import PaymentRepository
from app.storage.local import LocalStorage
from app.services.qr_reader import QRReaderService
from app.services.ocr_reader import OCRReaderService
from app.services.hash_service import HashService
from app.core.config import settings

router = APIRouter()

# Initialize services (could be done via dependencies)
qr_service = QRReaderService()
ocr_service = OCRReaderService()
hash_service = HashService()
storage = LocalStorage()

@router.post("/upload-slip")
async def upload_slip(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Validation
    content_type = file.content_type
    if content_type not in ["image/jpeg", "image/png"]:
        return {
            "success": false,
            "message": "Invalid file type. Only JPG, JPEG, and PNG are allowed."
        }
    
    file_content = await file.read()
    if len(file_content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds limit")

    repo = PaymentRepository(db)
    service = VerificationService(repo, storage, qr_service, ocr_service, hash_service)
    
    result = await service.verify_slip(file_content, file.filename)
    
    if "error" in result:
        raise HTTPException(status_code=result["status_code"], detail=result["error"])
        
    return result
