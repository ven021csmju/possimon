from sqlalchemy.orm import Session
from fastapi import HTTPException
import models
import schemas

def create_order(db: Session, order: schemas.OrderCreate, user_id: int):
    # 1. Get unique product IDs and sort them to prevent deadlocks
    product_ids = sorted(list(set(item.product_id for item in order.items)))

    # Use a transaction block for atomicity
    try:
        # Check address for Online orders
        if order.order_type == schemas.OrderType.ONLINE:
            if not order.address_id:
                raise HTTPException(status_code=400, detail="Address is required for online orders")
            
            address = db.query(models.Address).filter(
                models.Address.id == order.address_id,
                models.Address.user_id == user_id
            ).first()
            if not address:
                raise HTTPException(status_code=404, detail="Address not found")

        # 2. Lock product rows to ensure atomic stock update
        products = db.query(models.Product).filter(
            models.Product.id.in_(product_ids)
        ).with_for_update().all()

        product_map = {p.id: p for p in products}

        # 3. Validate existence and stock
        for item in order.items:
            if item.product_id not in product_map:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
            
            product = product_map[item.product_id]
            if product.stock < item.quantity:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Insufficient stock for product {product.name} (ID: {product.id})"
                )

        # 4. Create Order
        db_order = models.Order(
            user_id=user_id,
            address_id=order.address_id,
            payment_method=models.PaymentMethod(order.payment_method.value),
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

        db_order.total_price = total_price

        # 5. Create Payment
        db_payment = models.Payment(
            order_id=db_order.id,
            method=models.PaymentMethod(order.payment_method.value),
            status="pending" # Initial status for payment record
        )
        db.add(db_payment)

        # Commit everything as one atomic unit
        db.commit()
        db.refresh(db_order)
        return db_order

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
