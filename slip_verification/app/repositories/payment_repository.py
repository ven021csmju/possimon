from sqlalchemy.orm import Session
from app.models.payment import Payment
from app.models.audit_log import PaymentLog
from typing import Optional

class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_payment(self, payment_data: dict) -> Payment:
        db_payment = Payment(**payment_data)
        self.db.add(db_payment)
        self.db.commit()
        self.db.refresh(db_payment)
        return db_payment

    def get_by_hash(self, image_hash: str) -> Optional[Payment]:
        return self.db.query(Payment).filter(Payment.image_hash == image_hash).first()

    def get_by_ref_no(self, ref_no: str) -> Optional[Payment]:
        return self.db.query(Payment).filter(Payment.reference_no == ref_no).first()

    def create_log(self, payment_id: str, action: str, message: str):
        log = PaymentLog(payment_id=payment_id, action=action, message=message)
        self.db.add(log)
        self.db.commit()
