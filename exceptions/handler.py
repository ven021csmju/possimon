from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from .base_exception import AppException
from core.logging_config import logger

def register_exception_handlers(app: FastAPI):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning(
            f"AppException: code={exc.code}, message={exc.message}, path={request.url.path}, method={request.method}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "code": exc.code
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(
            f"HTTPException: status={exc.status_code}, detail={exc.detail}, path={request.url.path}, method={request.method}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "code": f"HTTP_{exc.status_code}"
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            f"Unhandled Exception: {str(exc)}, path={request.url.path}, method={request.method}", 
            exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal Server Error",
                "code": "INTERNAL_SERVER_ERROR",
                "detail": str(exc)
            },
        )
