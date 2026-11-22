import httpx

from app.config import settings
from app.platforms.base import Platform


class SlackPlatform(Platform):
    name = "slack"

    @property
    def is_configured(self) -> bool:
        return bool(settings.slack_webhook_url)

    async def _post(self, message: str) -> tuple[str | None, bool | None]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                settings.slack_webhook_url, json={"text": message}
            )
            response.raise_for_status()
            # Slack's incoming webhook returns the literal body "ok" on
            # success, not JSON, and never returns a message link or id.
            if response.text.strip().lower() != "ok":
                raise RuntimeError(f"unexpected Slack response: {response.text}")

        return None, False  # Slack channels require workspace membership
