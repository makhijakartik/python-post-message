import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)

VALID_MESSAGE = "Check out our new launch! Visit https://example.com for details."


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_rejects_message_over_200_chars():
    message = "a" * 195 + " https://example.com"
    response = client.post("/posting", json={"message": message})
    assert response.status_code == 422


def test_rejects_message_without_link():
    response = client.post("/posting", json={"message": "No link here at all."})
    assert response.status_code == 422


def test_rejects_message_with_multiple_links():
    message = "See https://example.com and also https://example.org"
    response = client.post("/posting", json={"message": message})
    assert response.status_code == 422


def test_rejects_invalid_url_scheme():
    message = "Check this out ftp://example.com for more info"
    response = client.post("/posting", json={"message": message})
    assert response.status_code == 422


def test_rejects_empty_message():
    response = client.post("/posting", json={"message": "   "})
    assert response.status_code == 422


def test_accepts_valid_message_shape():
    response = client.post("/posting", json={"message": VALID_MESSAGE})
    assert response.status_code == 200
    body = response.json()
    assert "success" in body
    assert "results" in body
    assert len(body["results"]) == 5


# ---------------------------------------------------------------------------
# Platform orchestration — all platforms unconfigured by default in tests
# ---------------------------------------------------------------------------


def test_unconfigured_platforms_are_skipped_not_failed():
    for field in (
        "discord_webhook_url",
        "slack_webhook_url",
        "telegram_bot_token",
        "telegram_chat_id",
        "mastodon_access_token",
        "teams_webhook_url",
    ):
        assert getattr(settings, field) is None

    response = client.post("/posting", json={"message": VALID_MESSAGE})
    body = response.json()
    assert body["success"] is False  # nothing configured -> nothing succeeded
    for result in body["results"]:
        assert result["status"] == "skipped"
        assert result["error"] is not None


# ---------------------------------------------------------------------------
# Platform orchestration — mocked HTTP, isolated failures
# ---------------------------------------------------------------------------


@respx.mock
def test_one_platform_failing_does_not_block_others(monkeypatch):
    monkeypatch.setattr(settings, "discord_webhook_url", "https://discord.com/api/webhooks/1/token")
    monkeypatch.setattr(settings, "slack_webhook_url", "https://hooks.slack.com/services/x/y/z")

    respx.post(url__startswith="https://discord.com/api/webhooks/1/token").mock(
        return_value=httpx.Response(
            200, json={"id": "999", "channel_id": "123"}
        )
    )
    respx.post("https://hooks.slack.com/services/x/y/z").mock(
        return_value=httpx.Response(500, text="internal_error")
    )

    response = client.post("/posting", json={"message": VALID_MESSAGE})
    assert response.status_code == 200
    body = response.json()

    by_platform = {r["platform"]: r for r in body["results"]}
    assert by_platform["discord"]["status"] == "success"
    assert by_platform["slack"]["status"] == "failed"
    assert by_platform["slack"]["error"]
    # overall success is true because at least one platform succeeded
    assert body["success"] is True


@respx.mock
def test_mastodon_success_returns_public_url(monkeypatch):
    monkeypatch.setattr(settings, "mastodon_access_token", "fake-token")
    monkeypatch.setattr(settings, "mastodon_instance_url", "https://mastodon.social")

    respx.post("https://mastodon.social/api/v1/statuses").mock(
        return_value=httpx.Response(
            200, json={"url": "https://mastodon.social/@bot/123456789"}
        )
    )

    response = client.post("/posting", json={"message": VALID_MESSAGE})
    body = response.json()
    mastodon_result = next(r for r in body["results"] if r["platform"] == "mastodon")
    assert mastodon_result["status"] == "success"
    assert mastodon_result["posted_url"] == "https://mastodon.social/@bot/123456789"
    assert mastodon_result["public_access"] is True
