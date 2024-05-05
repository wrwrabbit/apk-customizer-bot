# apk-builder-bot

A bot that builds an apk for P-Telegram

## Configuration
In order to use bot obtain a token from [BotFather](https://t.me/botfather).
Set the variable `TOKEN` in [.env](./.env) to the obtained token.

In order to use the local server obtain `API_ID` and `API_HASH`
following the instructions at <https://my.telegram.org>
and set them accordingly in [.env](./.env).

At the development stage it is possible to mock build process instead of actually running them by setting the variable `MOCK_BUILD` to any *non-empty* value.
In the mock mode it is possible to emulate build failure by setting the order's application ID to a string containing "error", e.g., `org.error.app`.

Example of .env file (without real values)
```
TELEGRAM_API_ID=0000000
TELEGRAM_API_HASH=asdadasdasdasda
SKIP_UPDATES=False
DELETE_MESSAGES_AFTER_SEC=3600
POSTGRES_USER=user
POSTGRES_PASSWORD=password
TOKEN=000000000:aaaaaaaaaaaaaaaaaaaaaaaaaaaaa
DATA_DIR=./data
TMP_DIR=${DATA_DIR}/tmp
MOCK_BUILD=False
```

## Deployment

1. Deploy server and api proxy

`docker compose up -d postgres tg_bot_api`

2. Run migrations

`docker compose up --build migrations`

3. Deploy workers

`docker compose up --build -d build_worker clean_orders_queue`

4. Run tests

`docker compose up --build tests`

5. Run bot

`docker compose up --build -d bot`

## Migrations

Create migration after changes in models
```bash
alembic revision --autogenerate -m "commit message"
```

Upgrade current database to latest version
```bash
alembic upgrade head
```

## Containers description

`postgres` - database

`tg_bot_api` - [api](https://hub.docker.com/r/aiogram/telegram-bot-api) for telegram bot

`build_worker` - Worker looking for prepared tasks and run build script to create apk. 
Uses docker-in-docker to compile apk. 
Second docker uses socket of host machine, so volume path must start from host machine path, not from current container path.

`clean_orders_queue` - Worker removing completed tasks from db
