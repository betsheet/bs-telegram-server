from util.config import logger, API_BASE_URL, PROCESS_PICK_MESSAGES_ENDPOINT
from bstelegramuser import BSTelegramUserClient
from bsutils.apimodels.api_responses import TelegramAppCredentialsResponse


class TelegramClientManager:

    def __init__(self) -> None:
        self._clients: dict[str, BSTelegramUserClient] = {}

    def create(self, user_id: str, phone_number: str, credentials: TelegramAppCredentialsResponse) -> BSTelegramUserClient:
        """Crea y registra una nueva instancia de BSTelegramUserClient para el usuario."""
        if user_id in self._clients:
            self.remove(user_id)
            #raise ValueError(f"A client for user '{user_id}' already exists")

        client = BSTelegramUserClient(
            api_id=credentials.api_id,
            api_hash=credentials.api_hash,
            phone_number=phone_number,
            session_file_path=f"sessions/{user_id}.session",
            logger=logger,
            process_messages_endpoint=f"{API_BASE_URL}/{PROCESS_PICK_MESSAGES_ENDPOINT}",
        )
        self._clients[user_id] = client
        return client

    def get(self, user_id: str) -> BSTelegramUserClient:
        """Devuelve la instancia existente para el usuario."""
        client = self._clients.get(user_id)
        if client is None:
            raise KeyError(f"No client found for user '{user_id}'")
        return client

    def remove(self, user_id: str) -> None:
        """Elimina la instancia del usuario del registro."""
        self._clients.pop(user_id, None)

    def exists(self, user_id: str) -> bool:
        return user_id in self._clients


# Instancia única compartida por toda la aplicación
telegram_client_manager = TelegramClientManager()

