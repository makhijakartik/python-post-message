from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    discord_webhook_url: str | None = None

    slack_webhook_url: str | None = None

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    mastodon_instance_url: str = "https://mastodon.social"
    mastodon_access_token: str | None = None

    teams_webhook_url: str | None = None


settings = Settings()
