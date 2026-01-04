import logging
import os
from logging.handlers import RotatingFileHandler

handlers = [logging.StreamHandler()]

if os.getenv("VERCEL") is None:
    handlers.append(
        RotatingFileHandler(
            "APILOG.txt",
            maxBytes=50000000,
            backupCount=10
        )
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=handlers
)

LOGGER = logging.getLogger("A360API")