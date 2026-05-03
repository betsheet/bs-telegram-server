import httpx
from bsutils.apimodels.api_responses import TelegramAppCredentialsResponse
from fastapi import HTTPException

from util.config import logger, CREDENTIALS_ENDPOINT  # noqa: F401 – re-exported
from managers.telegram_client_manager import TelegramClientManager, telegram_client_manager

import os
from dotenv import load_dotenv

load_dotenv()

_BASE_URL: str = os.environ["API_BASE_URL"]
_TOKEN: str = os.environ["API_SERVICE_JWT_TOKEN"]


async def get_telegram_app_credentials() -> TelegramAppCredentialsResponse:
    url = f"{_BASE_URL}{CREDENTIALS_ENDPOINT}"
    headers = {"Authorization": f"Bearer {_TOKEN}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return TelegramAppCredentialsResponse.model_validate(response.json())


def ensure_session_exists(mgr: TelegramClientManager, user_id: str) -> None:
    """Raises HTTP 404 if there is no active session for the given user_id."""
    if not mgr.exists(user_id):
        raise HTTPException(
            status_code=404,
            detail=f"No active session found for user '{user_id}'.",
        )


async def verify_client_authentication_state(client, user_id: str) -> None:
    """Raises HTTP 401 if the client is not authenticated."""
    if not await client.is_authenticated():
        raise HTTPException(
            status_code=401,
            detail=f"User '{user_id}' is not authenticated.",
        )


def get_telegram_client_manager() -> TelegramClientManager:
    return telegram_client_manager
