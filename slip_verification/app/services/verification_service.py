from app.services.qr_reader import QRReaderService
from app.services.ocr_reader import OCRReaderService
from app.services.hash_service import HashService
from app.repositories.payment_repository import PaymentRepository
from app.models.payment import PaymentStatus
from app.storage.base import BaseStorage
import uuid
import os

class VerificationService:
    def __init__(
        self, 
        repository: PaymentRepository, 
        storage: BaseStorage,
        qr_service: QRReaderService,
        ocr_service: OCRReaderService,
        hash_service: HashService
    ):
        self.repo = repository
        self.storage = storage
        self.qr_service = qr_service
        self.ocr_service = ocr_service
        self.hash_service = hash_service

    async def verify_slip(self, file_content: bytes, original_filename: str):
        # 1. Hash Check
        image_hash = self.hash_service.generate_sha256(file_content)
        existing_payment = self.repo.get_by_hash(image_hash)
        if existing_payment:
            return {"error": "Duplicate image hash", "status_code": 409}

        # 2. Storage
        filename = f"{uuid.uuid4()}_{original_filename}"
        slip_url = self.storage.save(file_content, filename)

        # 3. QR Extraction
        qr_data = self.qr_service.extract_qr_data(file_content)
        
        # 4. OCR Extraction
        ocr_data = self.ocr_service.extract_data(file_content)

        # 5. Validation Logic
        status = PaymentStatus.PENDING_REVIEW
        verify_method = "OCR"
        
        if qr_data:
            status = PaymentStatus.VERIFIED
            verify_method = "QR"
        elif ocr_data.get("amount") and ocr_data.get("reference_no"):
            status = PaymentStatus.PENDING_REVIEW
            verify_method = "OCR"
        else:
            status = PaymentStatus.REJECTED
            verify_method = "FAILED"

        # 6. Save to DB
        payment_data = {
            "amount": ocr_data.get("amount"),
            "reference_no": ocr_data.get("reference_no") or f"TEMP_{uuid.uuid4().hex[:10]}",
            "image_hash": image_hash,
            "slip_url": slip_url,
            "verify_method": verify_method,
            "status": status
        }
        
        payment = self.repo.create_payment(payment_data)
        
        # 7. Audit Log
        self.repo.create_log(payment.id, "UPLOAD", f"File {original_filename} uploaded")
        self.repo.create_log(payment.id, f"{verify_method}_SUCCESS", f"Verification status: {status}")

        return {
            "success": True,
            "data": {
                "id": str(payment.id),
                "status": payment.status,
                "amount": float(payment.amount) if payment.amount else None,
                "reference_no": payment.reference_no,
                "verify_method": payment.verify_method
            },
            "message": "success"
        }
