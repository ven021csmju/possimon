from .base_exception import AppException

class AuthException(AppException):
    def __init__(self, message: str = "Authentication failed", code: str = "AUTH_ERROR", status_code: int = 401):
        super().__init__(message, code, status_code)
