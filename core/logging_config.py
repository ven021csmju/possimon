import logging
import sys
import os
from core.config import settings

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

LOGGER_NAME = "possimon"

def setup_logging():
    # Logging Format
    logging_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(logging_format)
    
    # Configure logger
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO if settings.ENV == "production" else logging.DEBUG)
    
    # Avoid duplicate handlers if setup_logging is called multiple times
    if not logger.handlers:
        # Stream Handler (Console)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        
        # File Handler
        file_handler = logging.FileHandler("logs/app.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Optional: Set specific levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    return logger

# Singleton-like access
logger = logging.getLogger(LOGGER_NAME)
