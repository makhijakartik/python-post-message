import re
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

URL_REGEX = re.compile(r"https?://[^\s]+", re.IGNORECASE)

MAX_MESSAGE_LENGTH = 200


class PostingRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be empty")

        urls = URL_REGEX.findall(value)
        if len(urls) == 0:
            raise ValueError("message must contain exactly one CTA link, found none")
        if len(urls) > 1:
            raise ValueError(
                f"message must contain exactly one CTA link, found {len(urls)}"
            )

        url = urls[0].rstrip(".,)!?\"'")
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"CTA link is not a valid http(s) URL: {url}")

        return value


class PlatformResult(BaseModel):
    platform: str
    status: str  # "success" | "failed" | "skipped"
    posted_url: str | None = None
    public_access: bool | None = None
    date: str
    time: str
    error: str | None = None


class PostingResponse(BaseModel):
    success: bool
    results: list[PlatformResult]
