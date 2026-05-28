from typing import Any, Optional
import models
from websocket.manager import manager
from core.logging_config import logger


async def emit_ws_notification(payload: dict) -> None:
    """Core function to broadcast a notification to all connected clients."""
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
    """Helper to build a standardized notification payload."""
    payload: dict[str, Any] = {
        "type": type,
        "message": message,
        "level": level,
        "timestamp": Any, # Could add actual timestamp if needed
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
    status_val = order.status.value if hasattr(order.status, "value") else str(order.status)
    # Using NEW_ORDER as requested in requirements
    await emit_ws_notification(
        build_notification(
            type="NEW_ORDER",
            title="New Order Received",
            message=f"Order #{order.id} created (total {order.total_price:.2f})",
            level="info",
            order_id=order.id,
            status=status_val,
        )
    )


async def notify_payment_success(order_id: int) -> None:
    """Alias for notify_order_paid to match requirement terminology."""
    await emit_ws_notification(
        build_notification(
            type="PAYMENT_SUCCESS",
            title="Payment Received",
            message=f"Order #{order_id} paid successfully",
            level="success",
            order_id=order_id,
            status="paid",
        )
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


async def notify_shift_alert(message: str, level: str = "warning") -> None:
    """Notification for employee shifts (Start/End/Alerts)."""
    await emit_ws_notification(
        build_notification(
            type="SHIFT_ALERT",
            title="Shift Alert",
            message=message,
            level=level,
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
