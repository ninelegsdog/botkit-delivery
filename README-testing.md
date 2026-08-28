# Testing guide — botkit-delivery

Test pyramid follows `Промпт автоматизация тестирования Telegram-бота.md`.

## Levels & markers

| marker | meaning | runs on |
|--------|---------|---------|
| `no_req` | fully offline (no network/Telegram) | every commit/PR |
| `req` | needs network / real Telegram account | only with `RUN_TELEGRAM_E2E=1` |
| `unit` | isolated unit test | – |
| `integration` | local component/integration (dispatcher/FSM/webhook) | – |
| `webhook` | webhook endpoint test | – |
| `e2e` | real Telegram E2E via MTProto (Telethon) | – |
| `serial` | must not be parallelized (`-n 0`) | – |

Offline tests are auto-tagged `no_req` in `tests/conftest.py::pytest_collection_modifyitems`.
Tests marked `req` are **skipped** unless `RUN_TELEGRAM_E2E=1` is set.

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
# for real E2E only:
pip install -e ".[e2e]"
```

## Commands

```bash
# offline suite (parallel)
pytest -m no_req -n auto

# coverage (branch)
pytest -m no_req -n auto --cov=src --cov-branch --cov-report=term-missing --cov-report=xml

# lint
ruff check .

# single group
pytest -m "no_req and webhook" -n auto
```

## Webhook secret

Unlike botkit-bookingbot (which uses aiogram `SimpleRequestHandler` with
`X-Telegram-Bot-Api-Secret-Token`), botkit-delivery exposes its webhook through a
plain **aiohttp** app in `src/delivery/webhook_api.py`. The delivery-status
endpoint `POST /webhook/status` enforces the `X-Webhook-Secret` header.
`tests/test_webhook.py` asserts:

- valid secret (`X-Webhook-Secret`) → 200/202
- wrong secret → 401/403
- missing secret → 401/403
- malformed JSON body → 4xx/5xx

The Telegram bot itself (`src/core/bot_factory.py`) is driven by aiogram
`Dispatcher`; bot/webhook handlers are tested via the dispatcher + `AsyncMock`
Bot session (see `tests/test_handlers.py`).

## Real Telegram E2E (opt-in)

1. Create a test bot via @BotFather → `TEST_BOT_USERNAME`, `TEST_BOT_TOKEN`.
2. Create a separate Telegram **user** account for automation.
3. Get `api_id`/`api_hash` at https://my.telegram.org → API development tools.
4. `TELEGRAM_API_ID=... TELEGRAM_API_HASH=... python scripts/generate_telegram_session.py`
   → prints a `StringSession` string. Store it as `TELEGRAM_SESSION_STRING` (secret).
5. Add to `.env`:

```dotenv
TEST_BOT_USERNAME=my_test_bot
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_SESSION_STRING=
TELEGRAM_E2E_TIMEOUT=20
RUN_TELEGRAM_E2E=0
```

6. Run: `RUN_TELEGRAM_E2E=1 pytest -m "req and e2e" -n 0 -vv`

E2E waits for replies via `asyncio.Event` + `wait_for` — **no `sleep`**.
Each run uses a unique correlation token. Do not parallelize a single account.

## Secrets

Never commit tokens/hashes/session strings. `.gitignore` covers `.env`, `*.session`.
If a session string leaks, revoke the Telegram session immediately and regenerate.

## Coverage target

Current gate: `fail_under = 54` (branch). Documented target is **80%**; raise it as
more business-logic tests land.

## Known limitations

- Real E2E requires accounts/secrets you must provision; it stays skipped in CI.
- `ptbtest` / original Pyrogram are intentionally avoided; Telethon (MTProto) is used
  for real-account E2E with a `pytest.importorskip` guard so collection never fails
  without the `e2e` extras installed.
