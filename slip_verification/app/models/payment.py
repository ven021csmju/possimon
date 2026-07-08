import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
import enum

class VerifyMethod(str, enum.Enum):
    QR = "QR"
    OCR = "OCR"
    MANUAL = "MANUAL"

class PaymentStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    PENDING_REVIEW = "PENDING_REVIEW"
    REJECTED = "REJECTED"

class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    amount = Column(Numeric(10, 2), nullable=True)
    reference_no = Column(String(100), unique=True, index=True)
    transfer_datetime = Column(DateTime, nullable=True)
    sender_bank = Column(String(100), nullable=True)
    image_hash = Column(String(255), unique=True, index=True)
    slip_url = Column(Text)
    verify_method = Column(String(20))
    status = Column(String(20), default=PaymentStatus.PENDING_REVIEW)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
