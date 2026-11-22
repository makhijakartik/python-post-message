import httpx

from app.config import settings
from app.platforms.base import Platform


class TelegramPlatform(Platform):
    name = "telegram"

    @property
    def is_configured(self) -> bool:
        return bool(settings.telegram_bot_token and settings.telegram_chat_id)

    async def _post(self, message: str) -> tuple[str | None, bool | None]:
        api_url = (
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        )
        chat_id = settings.telegram_chat_id

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                api_url, json={"chat_id": chat_id, "text": message}
            )
            response.raise_for_status()
            data = response.json()

        if not data.get("ok"):
            raise RuntimeError(f"Telegram API error: {data.get('description')}")

        result = data["result"]
        message_id = result.get("message_id")

        # Public channels are addressed by @username; those get a stable
        # t.me link. Private chats/groups (numeric chat ids) have no public URL.
        if chat_id.startswith("@") and message_id:
            posted_url = f"https://t.me/{chat_id.lstrip('@')}/{message_id}"
            public_access = True
        else:
            posted_url = None
            public_access = False

        return posted_url, public_access
