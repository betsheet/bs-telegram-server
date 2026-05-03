"""
test.py – Script de pruebas para procesar los N últimos mensajes de una lista de canales.
"""

import asyncio
import os
import shutil
import tempfile

import httpx
from bsutils.logger.bslogger import BSLogger
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL: str = os.environ["API_BASE_URL"]
API_TOKEN: str = os.environ["API_SERVICE_JWT_TOKEN"]
CREDENTIALS_ENDPOINT: str = os.environ["GET_TELEGRAM_APP_CREDENTIALS_ENDPOINT"]
PROCESS_MESSAGES_ENDPOINT: str = os.environ["PROCESS_TELEGRAM_MESSAGES_ENDPOINT"]


async def get_credentials():
    url = f"{API_BASE_URL}{CREDENTIALS_ENDPOINT}"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    async with httpx.AsyncClient() as http:
        resp = await http.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def post_message(http: httpx.AsyncClient, message: dict) -> dict:
    url = f"{API_BASE_URL}{PROCESS_MESSAGES_ENDPOINT}"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    resp = await http.post(url, json=message, headers=headers)
    resp.raise_for_status()
    return resp.json()


USER_ID = "68d97d664d8fc5de568bd3ed"
PHONE_NUMBER = "+34614195139"


async def main() -> None:
    from bstelegramuser import BSTelegramUserClient

    testing_channels: list[str] = [
        #"Turkbasket - Solopicks"
        #"Tsonga7 - Solopicks",

        "Irish - Solopicks",
        #"Blade - Solopicks",
        #"Inmamolero Basic - Solopicks",
        #"Awer - Solopicks",
        #"Borja tips - Solopicks",
        #"Fusion Blog - Solopicks",
        #"Einstein - Solopicks",
        #"Turkbasket - Solopicks",
        #"Evente - Solopicks",
        #"Mallic - Solopicks",
        #"Grimacewood - Solopicks",
        #"SlavaG - Solopicks",
        #"Baskettips123 - Solopicks",
        #"Cristiano - Solopicks",
        #"Masseria - Solopicks",
        #"Visokiy - Solopicks",
        #"Benito - Solopicks",
        #"Picksenbase - Solopicks",
        #"CSGO - Solopicks",
    ]
    n = 50

    user_id = USER_ID

    print("Obteniendo credenciales de la API…")
    creds = await get_credentials()

    session_path = f"sessions/{user_id}.session"
    if not os.path.exists(session_path):
        raise FileNotFoundError(
            f"No se encontró la sesión '{session_path}'. "
            f"Sesiones disponibles: {os.listdir('sessions')}"
        )

    # Copiamos la sesión a un fichero temporal para evitar el error
    # "database is locked" cuando el servidor principal ya tiene la sesión abierta.
    tmp_session = tempfile.NamedTemporaryFile(suffix=".session", delete=False)
    tmp_session.close()
    shutil.copy2(session_path, tmp_session.name)
    print(f"Sesión copiada a fichero temporal: {tmp_session.name}")

    try:
        client = BSTelegramUserClient(
            api_id=creds["api_id"],
            api_hash=creds["api_hash"],
            phone_number=PHONE_NUMBER,
            session_file_path=tmp_session.name,
            logger=BSLogger("test_telegram_server"),
            process_messages_endpoint=f"{API_BASE_URL}{PROCESS_MESSAGES_ENDPOINT}",
        )

        print(f"Conectando cliente Telegram para el usuario '{user_id}'…")
        await client.connect_client()

        if not await client.is_authenticated():
            raise RuntimeError(f"El usuario '{user_id}' no está autenticado.")

        async with httpx.AsyncClient(timeout=360) as http:
            for channel in testing_channels:
                print(f"\n{'='*60}")
                print(f"Canal: {channel} — obteniendo los últimos {n} mensajes…")
                print(f"{'='*60}")

                messages = await client.get_messages_from_dialog(channel, n)
                print(f"  {len(messages)} mensajes encontrados. Procesando…\n")

                for msg in messages:
                    payload = {
                        "telegram_message_id": str(msg.id),
                        "from_user_id": user_id,
                        "from_telegram_chat_id": str(msg.chat.id),
                        "from_telegram_chat_name": msg.chat.title,
                        "content": msg.message or "",
                        "timestamp": msg.date.isoformat() if msg.date else None,
                    }
                    response = await post_message(http, payload)
                    total_picks = response.get("total_picks", 0)
                    print(f"  ✓ Mensaje {msg.id} → total_picks: {total_picks}")

                    if total_picks == 0:
                        print(f"\n  ⚠️  total_picks = 0. Contenido del mensaje:")
                        print(f"  {'-'*50}")
                        print(f"  {msg.message or '(sin texto)'}")
                        print(f"  {'-'*50}")
                        input("\n  Presiona Enter para continuar…\n")

        print(f"\n✅ Procesamiento completado para todos los canales.")
        await client.disconnect_client()

    finally:
        os.unlink(tmp_session.name)
        print(f"Fichero de sesión temporal eliminado.")


if __name__ == "__main__":
    asyncio.run(main())
