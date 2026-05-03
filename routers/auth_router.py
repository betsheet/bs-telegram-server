from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from managers.telegram_client_manager import TelegramClientManager
from util.util import get_telegram_app_credentials, get_telegram_client_manager

router = APIRouter(prefix="/auth", tags=["auth"])



# TODO: llevar a bsutils (requests/responses de bstelegramserver)
class RequestTelegramVerificationCodeRequest(BaseModel):
    user_id: str
    phone_number: str


class RequestTelegramVerificationCodeResponse(BaseModel):
    user_id: str
    phone_number: str
    already_authenticated: bool = False


class VerifyTelegramCodeRequest(BaseModel):
    user_id: str
    code: str


class VerifyTelegramCodeResponse(BaseModel):
    user_id: str
    authenticated: bool

# TODO: quizás el nombre del endpoint no es el más adecuado, ya que si el usuario está autenticado no se pedirá código
@router.post("/request-verification-code", response_model=RequestTelegramVerificationCodeResponse)
async def request_verification_code(
        body: RequestTelegramVerificationCodeRequest,
        mgr: TelegramClientManager = Depends(get_telegram_client_manager),
) -> RequestTelegramVerificationCodeResponse:
    """
    Recibe el número de teléfono y el user_id del sistema.
    Solicita el código de verificación a Telegram vía bstelegramuser.
    El usuario recibirá un código de autenticación en su app de Telegram
    """
    if mgr.exists(body.user_id):
        client = mgr.get(body.user_id)
    else:
        credentials = await get_telegram_app_credentials()
        client = mgr.create(
            user_id=body.user_id,
            phone_number=body.phone_number,
            credentials=credentials,
        )

    await client.connect_client()

    # En caso de que el usuario ya esté autenticado (es decir, tenemos un fichero de sesión válido para él),
    # no volvemos a pedirlo.
    if await client.is_authenticated():
        return RequestTelegramVerificationCodeResponse(
            user_id=body.user_id,
            phone_number=body.phone_number,
            already_authenticated=True,
        )

    await client.request_verification_code()
    return RequestTelegramVerificationCodeResponse(user_id=body.user_id, phone_number=body.phone_number)


@router.post("/verify-code", response_model=VerifyTelegramCodeResponse)
async def verify_code(
        body: VerifyTelegramCodeRequest,
        mgr: TelegramClientManager = Depends(get_telegram_client_manager),
) -> VerifyTelegramCodeResponse:
    """
    Recibe el user_id y el código de verificación enviado por Telegram.
    Completa el proceso de autenticación y genera el fichero de sesión.
    Devuelve error 404 si no existe ningún cliente iniciado para el user_id proporcionado.
    Devuelve error 400 si el código es incorrecto o la autenticación falla.
    """
    if not mgr.exists(body.user_id):
        raise HTTPException(
            status_code=404,
            detail=f"No active authentication session found for user '{body.user_id}'. "
                   "Request a verification code first.",
        )

    client = mgr.get(body.user_id)

    try:
        await client.verify_code(body.code)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Authentication failed: {str(e)}",
        )

    authenticated = await client.is_authenticated()
    return VerifyTelegramCodeResponse(user_id=body.user_id, authenticated=authenticated)


@router.get("/is-authenticated/{user_id}", response_model=VerifyTelegramCodeResponse)
async def is_authenticated(
        user_id: str,
        mgr: TelegramClientManager = Depends(get_telegram_client_manager),
) -> VerifyTelegramCodeResponse:
    """
    Recibe el user_id y comprueba si el usuario está autenticado.
    Devuelve error 404 si no existe ningún cliente activo para ese user_id.
    """
    if not mgr.exists(user_id):
        raise HTTPException(
            status_code=404,
            detail=f"No active authentication session found for user '{user_id}'.",
        )

    client = mgr.get(user_id)
    authenticated = await client.is_authenticated()
    return VerifyTelegramCodeResponse(user_id=user_id, authenticated=authenticated)



