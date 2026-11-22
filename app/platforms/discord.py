import httpx

from app.config import settings
from app.platforms.base import Platform


class DiscordPlatform(Platform):
    name = "discord"

    @property
    def is_configured(self) -> bool:
        return bool(settings.discord_webhook_url)

    async def _post(self, message: str) -> tuple[str | None, bool | None]:
        # ?wait=true makes Discord return the created message object instead
        # of an empty 204, so we can report back channel_id/message id.
        url = f"{settings.discord_webhook_url}?wait=true"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json={"content": message})
            response.raise_for_status()
            data = response.json()

        channel_id = data.get("channel_id")
        message_id = data.get("id")
        # A plain channel message link needs a guild id we don't have from
        # the webhook response; channel_id + message id is still enough for
        # anyone with channel access to jump to it via Discord's search.
        posted_url = (
            f"https://discord.com/channels/@me/{channel_id}/{message_id}"
            if channel_id and message_id
            else None
        )
        return posted_url, False  # Discord channels are not publicly indexable
