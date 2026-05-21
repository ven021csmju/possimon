from .base_exception import AppException

class OrderException(AppException):
    def __init__(self, message: str = "Order processing failed", code: str = "ORDER_ERROR", status_code: int = 400):
        super().__init__(message, code, status_code)
