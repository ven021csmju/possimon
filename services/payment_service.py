from sqlalchemy.orm import Session
from fastapi import HTTPException
import models

async def confirm_payment(order_id: int, db: Session, user, manager):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Allow if user is admin OR the owner of the order
    if user.role != "admin" and db_order.user_id != user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to confirm this payment")

    db_order.status = "paid"
    db.commit()

    # Notify all connected clients (especially the dashboard)
    await manager.broadcast({
        "type": "payment",
        "order_id": order_id,
        "status": "paid"
    })

    return {"message": "Payment confirmed and notification sent"}
