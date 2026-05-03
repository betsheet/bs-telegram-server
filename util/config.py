import os

from bsutils.logger.bslogger import BSLogger
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL: str = os.environ["API_BASE_URL"]
CREDENTIALS_ENDPOINT: str = os.environ["GET_TELEGRAM_APP_CREDENTIALS_ENDPOINT"]
PROCESS_PICK_MESSAGES_ENDPOINT: str = os.environ["PROCESS_TELEGRAM_MESSAGES_ENDPOINT"]

logger: BSLogger = BSLogger("telegram_server.log")


def get_logger() -> BSLogger:
    return logger

