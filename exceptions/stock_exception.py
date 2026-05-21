from .base_exception import AppException

class StockException(AppException):
    def __init__(self, message: str = "Insufficient stock", code: str = "OUT_OF_STOCK", status_code: int = 400):
        super().__init__(message, code, status_code)
