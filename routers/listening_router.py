import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from managers.telegram_client_manager import TelegramClientManager
from util.util import verify_client_authentication_state, get_telegram_client_manager

router = APIRouter(prefix="/listening", tags=["listening"])




class StartListeningRequest(BaseModel):
    user_id: str
    channels_to_listen: list[str]


class StartListeningResponse(BaseModel):
    user_id: str
    listening_channels: list[str]


@router.post("/start-listening", response_model=StartListeningResponse)
async def start_listening(
        body: StartListeningRequest,
        mgr: TelegramClientManager = Depends(get_telegram_client_manager),
) -> StartListeningResponse:
    """
    Configures the Telegram client for the given user to listen for new messages
    from the specified channels and starts the listener in the background.

    Each channel can be specified by its display name or its @username (with or
    without the leading '@').

    Returns 404 if no active session exists for the user.
    Returns 401 if the user is not authenticated.
    Returns 400 if the channels list is empty or a channel value is invalid.
    """
    if not mgr.exists(body.user_id):
        raise HTTPException(
            status_code=404,
            detail=f"No active session found for user '{body.user_id}'.",
        )

    if not body.channels_to_listen:
        raise HTTPException(
            status_code=400,
            detail="'channels' must be a non-empty list.",
        )

    client = mgr.get(body.user_id)

    await verify_client_authentication_state(client, body.user_id)

    try:
        for channel in body.channels_to_listen:
            await client.add_channel_to_listen(channel)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add channel: {str(e)}")

    # create_task lanza la corutina de forma concurrente en el event loop de asyncio
    # y devuelve el control inmediatamente, sin bloquear la respuesta HTTP.
    asyncio.create_task(_run_listener(client, body.user_id))

    return StartListeningResponse(user_id=body.user_id, listening_channels=client.get_listening_channels())


async def _run_listener(client, user_id: str) -> None:
    """Background task that keeps the Telegram listener running."""
    try:
        await client.start_listening_channels()
    except Exception as exc:
        # Errors are surfaced in the server log; the background task must not crash silently.
        from util.util import logger
        logger.error(f"Listener for user '{user_id}' stopped with error: {exc}")

