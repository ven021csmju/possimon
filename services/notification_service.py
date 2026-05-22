from typing import Any, Optional
import models
from routers.websocket import manager
from core.logging_config import logger


async def emit_ws_notification(payload: dict) -> None:
    try:
        await manager.broadcast(payload)
        logger.debug(f"WS notification broadcast: type={payload.get('type')}")
    except Exception as e:
        logger.error(f"Failed to broadcast notification: {e}", exc_info=True)


def build_notification(
    type: str,
    message: str,
    *,
    title: Optional[str] = None,
    level: str = "info",
    order_id: Optional[int] = None,
    status: Optional[str] = None,
    product_id: Optional[int] = None,
    user_id: Optional[int] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": type,
        "message": message,
        "level": level,
    }
    if title:
        payload["title"] = title
    if order_id is not None:
        payload["orderId"] = order_id
    if status is not None:
        payload["status"] = status
    if product_id is not None:
        payload["productId"] = product_id
    if user_id is not None:
        payload["userId"] = user_id
    if extra:
        payload.update(extra)
    return payload


def is_low_stock(product: models.Product) -> bool:
    threshold = product.low_stock_alert if product.low_stock_alert is not None else 10
    return product.stock <= threshold


async def notify_low_stock(product: models.Product) -> None:
    if not is_low_stock(product):
        return
    threshold = product.low_stock_alert if product.low_stock_alert is not None else 10
    await emit_ws_notification(
        build_notification(
            type="LOW_STOCK",
            title="Low Stock Alert",
            message=f"{product.name} is low on stock ({product.stock} left, threshold {threshold})",
            level="warning",
            product_id=product.id,
        )
    )


async def notify_order_created(order: models.Order) -> None:
    status = order.status.value if hasattr(order.status, "value") else str(order.status)
    await emit_ws_notification(
        build_notification(
            type="ORDER_CREATED",
            title="New Order",
            message=f"Order #{order.id} created (total {order.total_price:.2f})",
            level="info",
            order_id=order.id,
            status=status,
        )
    )


async def notify_order_paid(order_id: int) -> None:
    message = f"Order #{order_id} paid successfully"
    await emit_ws_notification(
        build_notification(
            type="ORDER_PAID",
            title="Payment Received",
            message=message,
            level="success",
            order_id=order_id,
            status="paid",
        )
    )
    await emit_ws_notification(
        build_notification(
            type="ORDER_STATUS_UPDATE",
            title="Order Updated",
            message=f"Order #{order_id} status changed to paid",
            level="info",
            order_id=order_id,
            status="paid",
        )
    )
    await emit_ws_notification(
        {
            "type": "payment",
            "orderId": order_id,
            "status": "paid",
            "message": message,
        }
    )


async def notify_payment_failed(order_id: int, reason: str = "Payment failed or timed out") -> None:
    await emit_ws_notification(
        build_notification(
            type="PAYMENT_FAILED",
            title="Payment Failed",
            message=f"Order #{order_id}: {reason}",
            level="error",
            order_id=order_id,
            status="failed",
        )
    )
    await emit_ws_notification(
        build_notification(
            type="ORDER_STATUS_UPDATE",
            title="Order Updated",
            message=f"Order #{order_id} payment failed",
            level="warning",
            order_id=order_id,
            status="failed",
        )
    )


async def notify_new_customer(user: models.User) -> None:
    name = user.first_name or user.username or user.email or "Customer"
    await emit_ws_notification(
        build_notification(
            type="NEW_CUSTOMER",
            title="New Customer",
            message=f"New customer registered: {name}",
            level="info",
            user_id=user.id,
        )
    )


async def post_order_created_side_effects(
    order: models.Order, products: list[models.Product]
) -> None:
    await notify_order_created(order)
    for product in products:
        await notify_low_stock(product)
