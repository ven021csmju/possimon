import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base

class PaymentLog(Base):
    __tablename__ = "payment_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=True)
    action = Column(String(100))
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
