# BotKit Delivery

Бот отслеживания доставки с приёмом событий из внешних систем по webhook.

Живой бот: @DeliveryKitBot · часть портфолио из 9 Telegram-ботов на Python.

## Возможности

- Статусы доставки и история изменений
- Подписка клиента на отслеживание заказа
- Приём событий из внешних систем (`WEBHOOK_SECRET`) — API-интеграция
- Конечный автомат переходов статусов
- Админка, антифлуд, `/metrics`, Sentry

## Стек

- Python 3.12+
- aiogram 3.x
- SQLAlchemy 2 (async) + SQLite (WAL) / PostgreSQL
- Redis
- Prometheus `/metrics`
- Sentry
- Docker, webhook (prod) / polling (dev)

## Быстрый старт

```bash
cp .env.example .env      # заполнить BOT_TOKEN и ADMIN_IDS
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python -m src.bot
```

## Переменные окружения

ADMIN_IDS, ADMIN_PASSWORD, BOT_TOKEN, DB_PATH, LOG_LEVEL, METRICS_PORT, REDIS_URL, SENTRY_DSN, WEBHOOK_SECRET

Секреты не хранятся в git: `.env` в `.gitignore`, для переноса используется
шифрование age, в CI включён gitleaks-гейт.

## Тесты

```bash
pytest
```

84 теста в 24 файлах.

## Бэкапы

Бэкапы и восстановление — общий контур на проде (systemd-таймеры, offsite restic,
один общий Redis на все боты), а не отдельный скрипт внутри репозитория.
Актуальная процедура и оговорки — в
[`botkit-monitoring/ops/backup/RESTORE.md`](https://github.com/ninelegsdog/botkit-monitoring/blob/main/ops/backup/RESTORE.md).

```bash
# проверка бэкапа этого бота (ничего не меняет)
/root/restore_test.sh botkit-delivery
```

## Development process

Проект создан в AI-native процессе разработки: код производили AI coding-агенты
в настроенном мной agent harness — то есть по слотам требований, инструкций, ограничений
и критериев приёмки, которые я задал заранее.

Моя роль в проекте:

- продуктовая постановка и пользовательские сценарии;
- декомпозиция задачи на самостоятельные инженерные этапы;
- context engineering: инструкции, ограничения и рабочие правила для агентов;
- управление контекстным окном между итерациями;
- цикл «спецификация → генерация → запуск → проверка → исправление»;
- валидация результата, тестирование, ревью;
- контроль структуры репозитория, конфигурации, документации и воспроизводимости запуска.

Implementation code was generated with AI coding agents under human-led engineering control.

Полное описание процесса, шаблон `AGENTS.md` и чек-листы ревью AI-кода и секретов —
в репозитории [agentic-development-playbook](https://github.com/ninelegsdog/agentic-development-playbook).

## Лицензия

MIT — см. [LICENSE](LICENSE).

## Статус

Проект работает в продакшене (webhook, TLS, health-check). Состояние: **production**.
