from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.schemas import PlatformResult


class Platform(ABC):
    """Base class for a single third-party posting integration.

    Subclasses must set `name` and implement `is_configured` and `_post`.
    `post()` is the only method the posting service calls; it standardizes
    timestamps and turns any exception into a failed PlatformResult instead
    of letting it propagate, so one platform's error can't take others down.
    """

    name: str = "platform"

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    async def _post(self, message: str) -> tuple[str | None, bool | None]:
        """Publish the message. Returns (posted_url, public_access)."""
        ...

    async def post(self, message: str) -> PlatformResult:
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        if not self.is_configured:
            return PlatformResult(
                platform=self.name,
                status="skipped",
                date=date_str,
                time=time_str,
                error="platform not configured (missing credentials)",
            )

        try:
            posted_url, public_access = await self._post(message)
        except Exception as exc:  # noqa: BLE001 - isolate failures per platform
            return PlatformResult(
                platform=self.name,
                status="failed",
                date=date_str,
                time=time_str,
                error=str(exc),
            )

        return PlatformResult(
            platform=self.name,
            status="success",
            posted_url=posted_url,
            public_access=public_access,
            date=date_str,
            time=time_str,
        )
