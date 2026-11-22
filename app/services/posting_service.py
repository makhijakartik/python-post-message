import asyncio

from app.platforms.base import Platform
from app.platforms.discord import DiscordPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.slack import SlackPlatform
from app.platforms.teams import TeamsPlatform
from app.platforms.telegram import TelegramPlatform
from app.schemas import PlatformResult, PostingResponse


def get_platforms() -> list[Platform]:
    return [
        DiscordPlatform(),
        SlackPlatform(),
        TelegramPlatform(),
        MastodonPlatform(),
        TeamsPlatform(),
    ]


async def post_message(message: str) -> PostingResponse:
    platforms = get_platforms()

    # Each platform's post() already catches its own exceptions and returns
    # a PlatformResult, so gather() here only ever sees successful awaitables
    # — one platform being down never cancels or blocks the others.
    results: list[PlatformResult] = await asyncio.gather(
        *(platform.post(message) for platform in platforms)
    )

    overall_success = any(r.status == "success" for r in results)
    return PostingResponse(success=overall_success, results=results)
