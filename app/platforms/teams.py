import httpx

from app.config import settings
from app.platforms.base import Platform


class TeamsPlatform(Platform):
    name = "microsoft_teams"

    @property
    def is_configured(self) -> bool:
        return bool(settings.teams_webhook_url)

    async def _post(self, message: str) -> tuple[str | None, bool | None]:
        # Legacy "Connector" MessageCard format; accepted by both classic
        # Office 365 Connectors and most Workflows-based incoming webhooks.
        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": "Automated post",
            "text": message,
        }

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(settings.teams_webhook_url, json=payload)
            response.raise_for_status()
            if response.text.strip() != "1":
                raise RuntimeError(f"unexpected Teams response: {response.text}")

        # Teams incoming webhooks don't return a message link or id at all.
        return None, False
