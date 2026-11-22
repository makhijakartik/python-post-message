# Automated Multi-Platform Posting System

FastAPI service that accepts a short promotional message with a single CTA
link, validates it, and publishes it independently to 5 third-party
platforms via their official APIs. One platform failing (bad credentials,
timeout, rate limit) never blocks the others — every platform gets its own
isolated attempt and its own reported outcome.

## Platforms integrated

| Platform | Integration | Docs |
|---|---|---|
| Discord | Incoming Webhook | https://discord.com/developers/docs/resources/webhook |
| Slack | Incoming Webhook | https://api.slack.com/messaging/webhooks |
| Telegram | Bot API `sendMessage` | https://core.telegram.org/bots/api#sendmessage |
| Mastodon | REST API `POST /api/v1/statuses` | https://docs.joinmastodon.org/methods/statuses/#create |
| Microsoft Teams | Incoming Webhook (MessageCard) | https://learn.microsoft.com/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook |

Each platform is skipped (not failed) if its credentials aren't set in
`.env` — this keeps local testing honest without any platform faking success.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in the credentials you want to test with
```

Getting credentials for each platform (free, a few minutes each):

- **Discord** — Server Settings → Integrations → Webhooks → New Webhook → Copy URL.
- **Slack** — create an app at api.slack.com/apps → Incoming Webhooks → Add New Webhook to Workspace.
- **Telegram** — message `@BotFather` to create a bot and get a token; add the bot as admin to a channel/group and use its chat id (public channels can use `@channelname`).
- **Mastodon** — on any instance (e.g. mastodon.social): Settings → Development → New Application with `write:statuses` scope.
- **Microsoft Teams** — a channel's Connectors (or "Workflows" → *Post to a channel when a webhook request is received*) → copy the webhook URL.

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Interactive docs: http://localhost:4000/docs

## Sample request

```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Check out our new launch! Visit https://example.com for details."}'
```

## Sample response

```json
{
  "success": true,
  "results": [
    {
      "platform": "discord",
      "status": "success",
      "posted_url": "https://discord.com/channels/@me/123456789/987654321",
      "public_access": false,
      "date": "2026-11-22",
      "time": "10:52:37",
      "error": null
    },
    {
      "platform": "slack",
      "status": "success",
      "posted_url": null,
      "public_access": false,
      "date": "2026-11-22",
      "time": "10:52:37",
      "error": null
    },
    {
      "platform": "telegram",
      "status": "skipped",
      "posted_url": null,
      "public_access": null,
      "date": "2026-11-22",
      "time": "10:52:37",
      "error": "platform not configured (missing credentials)"
    },
    {
      "platform": "mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@yourbot/113456789012345678",
      "public_access": true,
      "date": "2026-11-22",
      "time": "10:52:37",
      "error": null
    },
    {
      "platform": "microsoft_teams",
      "status": "failed",
      "posted_url": null,
      "public_access": null,
      "date": "2026-11-22",
      "time": "10:52:37",
      "error": "Client error '404 Not Found' for url '...'"
    }
  ]
}
```

`success` is `true` whenever at least one platform succeeds — a single
provider outage or missing credential never makes the whole request look
like a failure.

### `public_access` and `posted_url`, honestly

Not every provider gives back a link or exposes the post publicly:

- **Mastodon** posts with `visibility=public` → real, federated, publicly
  viewable URL.
- **Telegram** → public URL only if the chat id is a `@username` public
  channel; private chats/groups get no link.
- **Discord / Slack / Teams** webhooks don't expose a durable public URL to
  non-members — `posted_url` is `null`/internal-only and `public_access` is
  `false`. This is reported as-is rather than fabricated, since a fake link
  would misrepresent what actually happened.

### Validation errors

```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "No link in this message"}'
```

```json
{
  "success": false,
  "error": "validation_failed",
  "details": [
    {
      "type": "value_error",
      "loc": ["body", "message"],
      "msg": "Value error, message must contain exactly one CTA link, found none",
      "input": "No link in this message"
    }
  ]
}
```

Rules enforced: message is 1–200 characters, and contains **exactly one**
`http(s)://` URL (validated for scheme + host). Zero or multiple links, or a
non-http(s) URL, are rejected with a 422 and a clear reason.

## Architecture

```
app/
  main.py                 # FastAPI app, /posting route, validation error handler
  schemas.py              # PostingRequest (validation), PlatformResult, PostingResponse
  config.py                # env-driven credentials (pydantic-settings)
  platforms/
    base.py               # Platform ABC: post() standardizes timing + isolates exceptions
    discord.py / slack.py / telegram.py / mastodon.py / teams.py
  services/
    posting_service.py    # fans out to all platforms concurrently via asyncio.gather
tests/
  test_posting.py         # validation tests + mocked HTTP (respx) for success/failure/skip
```

Adding a 6th platform means dropping in one more `Platform` subclass and
registering it in `posting_service.get_platforms()` — nothing else changes.

## Tests

```bash
pytest -q
```

9 tests covering: message-length/link-count/URL-scheme validation, all
platforms reporting `skipped` when unconfigured, one platform failing
without blocking a concurrent success, and a platform returning a real
public URL.

## Notes / assumptions

- Platform selection is fixed internally (Discord, Slack, Telegram,
  Mastodon, Microsoft Teams) — the caller only supplies the message, per the
  spec.
- Twitter/X and Reddit were deliberately not used: X's free tier no longer
  allows posting without a paid plan, and Reddit's API requires app-review /
  account-karma gating that isn't appropriate for a short practical test.
- No secrets are committed; `.env` is gitignored, `.env.example` only has
  placeholders.
