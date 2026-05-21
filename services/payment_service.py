from sqlalchemy.orm import Session
from exceptions.not_found_exception import NotFoundException
from exceptions.auth_exception import AuthException
import models
from core.logging_config import logger

async def confirm_payment(order_id: int, db: Session, user, manager):
    logger.info(f"Confirming payment for order_id={order_id} by user_id={user.id}")
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        logger.warning(f"Payment confirmation failed: Order {order_id} not found")
        raise NotFoundException(message="Order not found", code="ORDER_NOT_FOUND")
    
    # Allow if user is admin OR the owner of the order
    if user.role != "admin" and db_order.user_id != user.id:
        logger.warning(f"User {user.id} unauthorized to confirm payment for order {order_id}")
        raise AuthException(
            message="You do not have permission to confirm this payment",
            code="PERMISSION_DENIED",
            status_code=403
        )

    if db_order.status == "paid":
        logger.info(f"Order {order_id} is already marked as paid")
        return {"message": "Order is already paid"}

    try:
        db_order.status = "paid"
        
        # Also update the associated payment record if it exists
        payment = db.query(models.Payment).filter(models.Payment.order_id == order_id).first()
        if payment:
            payment.status = "success"
            
        db.commit()
        logger.info(f"Order {order_id} status updated to 'paid' in DB")

        # Notify all connected clients (especially the dashboard)
        await manager.broadcast({
            "type": "payment",
            "order_id": order_id,
            "status": "paid"
        })
        logger.debug(f"Broadcasted payment confirmation for order {order_id}")

        return {"message": "Payment confirmed and notification sent"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error during payment confirmation for order {order_id}: {str(e)}", exc_info=True)
        # Use AppException for wrapped internal error or let global handler handle it
        raise AuthException(message="Internal server error during payment confirmation", code="PAYMENT_CONFIRM_ERROR", status_code=500)
