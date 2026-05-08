from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from auth.dependencies import get_db, get_current_user
from services.qr_service import generate_qr_response
from services.payment_service import confirm_payment as confirm_payment_service
from routers.websocket import manager
import models

router = APIRouter()

@router.get("/generate-qr")
async def generate_qr(
    phone: str = Query(..., min_length=10, max_length=13),
    amount: float = Query(..., gt=0),
    current_user: models.User = Depends(get_current_user),
):
    return generate_qr_response(phone, amount)

@router.post("/confirm-payment/{order_id}")
async def confirm_payment(
    order_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    return await confirm_payment_service(order_id, db, current_user, manager)
