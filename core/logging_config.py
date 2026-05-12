import logging
import sys
from core.config import settings

def setup_logging():
    # Logging Format
    logging_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO if settings.ENV == "production" else logging.DEBUG,
        format=logging_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("app.log", encoding="utf-8")
        ]
    )
    
    # Optional: Set specific levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logger = logging.getLogger("possimon")
    logger.info(f"Logging initialized in {settings.ENV} mode")
    
    return logger

logger = logging.getLogger("possimon")
