from bstelegramuser.bstelegramuser import TelegramDialog
from bsutils.apimodels.pick_message import BSTelegramMessage
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from managers.telegram_client_manager import TelegramClientManager
from util.util import verify_client_authentication_state, get_telegram_client_manager, ensure_session_exists
from services.channels_service import get_n_messages_kway_merge

router = APIRouter(prefix="/channels", tags=["channels"])



class UserDialogsResponse(BaseModel):
    user_id: str
    dialogs: list[TelegramDialog]


class DialogMessagesResponse(BaseModel):
    user_id: str
    messages: list[BSTelegramMessage]


class DialogMessagesRequest(BaseModel):
    channel_names: list[str]
    n: int

    @field_validator("n")
    @classmethod
    def n_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("'n' must be a positive integer.")
        return v

    @field_validator("channel_names")
    @classmethod
    def channel_names_must_not_be_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("'channel_names' must contain at least one channel.")
        return v


class DialogUsernameResponse(BaseModel):
    user_id: str
    channel_name: str
    username: str | None



@router.get("/{user_id}", response_model=UserDialogsResponse)
async def get_user_dialogs(
        user_id: str,
        mgr: TelegramClientManager = Depends(get_telegram_client_manager),
) -> UserDialogsResponse:
    """
    Devuelve la lista de nombres de canales y supergrupos a los que pertenece el usuario.
    Devuelve error 404 si no existe ningún cliente activo para ese user_id.
    Devuelve error 401 si el usuario no está autenticado.
    """
    ensure_session_exists(mgr, user_id)

    client = mgr.get(user_id)
    # TODO: igual podríamos simplificar esto, usando sólo la id y obteniendo el cliente dentro de esa función, ya que no se usa más
    await verify_client_authentication_state(client, user_id)

    try:
        dialogs = await client.get_user_dialogs(None)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve dialogs: {str(e)}",
        )

    return UserDialogsResponse(user_id=user_id, dialogs=dialogs)




@router.post("/{user_id}/messages", response_model=DialogMessagesResponse)
async def get_last_n_messages_from_channels(
        user_id: str,
        body: DialogMessagesRequest,
        mgr: TelegramClientManager = Depends(get_telegram_client_manager),
) -> DialogMessagesResponse:
    """
    Devuelve los n últimos mensajes del conjunto de canales indicados para el usuario,
    ordenados de más reciente a más antiguo. Cada mensaje incluye el nombre del canal de origen.
    Devuelve error 404 si no existe ningún cliente activo para ese user_id.
    Devuelve error 401 si el usuario no está autenticado.
    Devuelve error 404 si no se encuentra alguno de los canales indicados.
    Devuelve error 400 si n no es un entero positivo o la lista de canales está vacía.
    """
    ensure_session_exists(mgr, user_id)

    client = mgr.get(user_id)

    await verify_client_authentication_state(client, user_id)

    # K-way merge: fetches only as many messages as needed across all channels.
    messages = await get_n_messages_kway_merge(client, body.channel_names, body.n, user_id)

    return DialogMessagesResponse(user_id=user_id, messages=messages)


"""
TODO: necesito poder obtener sólo dialogs del tipo indicado, aceptándolo en la petición.
"""


@router.post("/{user_id}/get-dialog-username", response_model=DialogUsernameResponse)
async def get_channel_username(
        user_id: str,
        body: dict,
        mgr: TelegramClientManager = Depends(get_telegram_client_manager),
) -> DialogUsernameResponse:
    """
    Devuelve el username (@handle) del canal indicado.
    Devuelve error 404 si no existe ningún cliente activo para ese user_id.
    Devuelve error 401 si el usuario no está autenticado.
    Devuelve error 404 si no se encuentra el canal con ese nombre.
    """
    ensure_session_exists(mgr, user_id)

    client = mgr.get(user_id)

    await verify_client_authentication_state(client, user_id)

    try:
        username = await client.get_dialog_username_by_name(body["dialog_name"])
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve username: {str(e)}")

    return DialogUsernameResponse(user_id=user_id, channel_name=body['dialog_name'], username=username)
