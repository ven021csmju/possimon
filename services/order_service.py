from sqlalchemy.orm import Session
from fastapi import HTTPException
import models
import schemas
import logging

logger = logging.getLogger("possimon")

def normalize_payment_method(payment_method: schemas.PaymentMethod):
    if payment_method == schemas.PaymentMethod.QR:
        return models.PaymentMethod.PROMPTPAY
    return models.PaymentMethod(payment_method.value)

def create_order(db: Session, order: schemas.OrderCreate, user_id: int):
    logger.info(f"Creating order for user_id={user_id}, type={order.order_type}, items_count={len(order.items)}")
    # 1. Ensure all items have a valid product_id
    for item in order.items:
        if not item.product_id:
            # Fallback to SKU resolution if product_id is missing (though schemas now require it)
            if item.sku:
                product = db.query(models.Product).filter(models.Product.sku == item.sku).first()
                if product:
                    item.product_id = product.id
                else:
                    logger.warning(f"Product SKU '{item.sku}' not found during order creation")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Product with SKU '{item.sku}' not found and no product_id provided"
                    )
            else:
                logger.warning("Order item missing both product_id and sku")
                raise HTTPException(status_code=400, detail="Each item must have a product_id or a valid sku")

    # 2. Get unique product IDs and sort them to prevent deadlocks
    product_ids = sorted(list(set(item.product_id for item in order.items)))

    # Use a transaction block for atomicity
    try:
        # Check address for Online orders - only if provided
        if order.order_type == schemas.OrderType.ONLINE and order.address_id:
            address = db.query(models.Address).filter(
                models.Address.id == order.address_id,
                models.Address.user_id == user_id
            ).first()
            if not address:
                logger.warning(f"Address ID {order.address_id} not found for user {user_id}")
                raise HTTPException(status_code=404, detail=f"Address ID {order.address_id} not found for this user")
        
        # 3. Lock product rows and validate existence in one go
        products = db.query(models.Product).filter(
            models.Product.id.in_(product_ids)
        ).with_for_update().all()

        product_map = {p.id: p for p in products}

        # 4. Validate stock and existence
        for item in order.items:
            if item.product_id not in product_map:
                logger.error(f"Product ID {item.product_id} unexpectedly not found after locking")
                raise HTTPException(status_code=404, detail=f"Product ID {item.product_id} not found in database")
            
            product = product_map[item.product_id]
            if product.stock < item.quantity:
                logger.warning(f"Insufficient stock for product {product.id} ({product.name}): Req={item.quantity}, Avail={product.stock}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Insufficient stock for product '{product.name}' (Requested: {item.quantity}, Available: {product.stock})"
                )

        payment_method = normalize_payment_method(order.payment_method)

        # 4. Create Order
        db_order = models.Order(
            user_id=user_id,
            address_id=order.address_id,
            payment_method=payment_method,
            order_type=models.OrderType(order.order_type.value),
            total_price=0,
            status=models.OrderStatus.PENDING
        )
        db.add(db_order)
        db.flush() # Get order.id

        total_price = 0
        for item in order.items:
            product = product_map[item.product_id]
            # Use selling_price if available, otherwise fallback to price
            item_price = product.selling_price if product.selling_price > 0 else product.price
            item_total = item_price * item.quantity
            total_price += item_total

            # Create OrderItem
            db_item = models.OrderItem(
                order_id=db_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item_price
            )
            db.add(db_item)

            # Update Stock
            product.stock -= item.quantity
            logger.debug(f"Reduced stock for product {product.id} by {item.quantity}. New stock: {product.stock}")

        db_order.total_price = total_price

        # 5. Create Payment
        db_payment = models.Payment(
            order_id=db_order.id,
            method=payment_method,
            status="pending" # Initial status for payment record
        )
        db.add(db_payment)

        # Commit everything as one atomic unit
        db.commit()
        db.refresh(db_order)
        logger.info(f"Order created successfully: order_id={db_order.id}, total={db_order.total_price}")
        return db_order

    except HTTPException as e:
        db.rollback()
        logger.warning(f"Order creation failed (Client Error): {e.detail}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Critical error during order creation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
