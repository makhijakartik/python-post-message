import httpx

from app.config import settings
from app.platforms.base import Platform


class MastodonPlatform(Platform):
    name = "mastodon"

    @property
    def is_configured(self) -> bool:
        return bool(settings.mastodon_access_token)

    async def _post(self, message: str) -> tuple[str | None, bool | None]:
        url = f"{settings.mastodon_instance_url}/api/v1/statuses"
        headers = {"Authorization": f"Bearer {settings.mastodon_access_token}"}

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                url,
                headers=headers,
                data={"status": message, "visibility": "public"},
            )
            response.raise_for_status()
            data = response.json()

        posted_url = data.get("url")
        return posted_url, True  # "public" visibility is federated/indexable
