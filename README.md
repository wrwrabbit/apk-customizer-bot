# apk-builder-bot

A bot that builds an apk for P-Telegram

## Configuration
In order to use bot obtain a token from [BotFather](https://t.me/botfather).
Set the variable `TOKEN` in [.env](./.env) to the obtained token.

In order to use the local server obtain `API_ID` and `API_HASH`
following the instructions at <https://my.telegram.org>
and set them accordingly in [.env](./.env).

Example of `.env.postgres` file (without real values)
```
POSTGRES_USER=user
POSTGRES_PASSWORD=password
```

Example of `.env.tg_bot_api` file (without real values)
```
TELEGRAM_API_ID=0000000
TELEGRAM_API_HASH=asdadasdasdasda
```

Example of `.env` file (without real values)
```
SKIP_UPDATES=False
DELETE_MESSAGES_AFTER_SEC=3600
DELETE_MESSAGES_WITHOUT_ORDERS_AFTER_SEC=1800
DELETE_MESSAGES_WITH_FINISHED_ORDERS_AFTER_SEC=86400
TOKEN=000000000:aaaaaaaaaaaaaaaaaaaaaaaaaaaaa
DATA_DIR=./data
TMP_DIR=./data/tmp
JWT_SECRET_KEY=CHANGE_ME
ADMIN_CHAT_ID=123456789
ERROR_LOGS_CHAT_ID=123456789
STATS_CHAT_ID=123456789
STATS_PERIOD=86400
CONSIDER_WORKER_OFFLINE_AFTER_SEC=1800
SALT_FOR_DERIVATION_RANDOM_SEED_FROM_USER_ID=CHANGE_ME
USER_ID_HASH_SALT=CHANGE_ME
FAILED_BUILD_COUNT_ALLOWED=1
DELETE_USER_BUILD_STATS_AFTER_SEC=5
UPDATES_ALLOWED=True
SET_BOT_NAME_AND_DESCRIPTION=False
DELAY_BEFORE_UPDATE_ORDER_BUILD_SEC=60
```

Copy all files with `.example` to the same location and remove `.example` suffix from the filename.

### Workers Controller Configuration

Replace `IP.1 = 127.0.0.1` with your ip in to `web/san.cnf`. Add your ip worker looking for prepared tasks and run build script to 
create apk
`IP.2 = 1.2.3.4` if needed.

```bash
cd web
openssl req -x509 -nodes -newkey rsa:4096 -keyout key.pem -out cert.pem -config san.cnf
```

Set up the HTTPS server. You can do it either **the easy way** (for development) 
or **the right way** (for production).

#### The Easy Way

Modify docker-compose.yaml. Replace 

```
    command: gunicorn -b 0.0.0.0:8000 web.workers_controller:app
    ports:
      - "127.0.0.1:8000:8000"
```

with

```
    command: gunicorn --certfile web/cert.pem --keyfile web/key.pem -b 0.0.0.0:8000 web.workers_controller:app
    ports:
      - "8000:8000"
```

#### The Right Way

Setup nginx reverse proxy. Example config:

```
server {
    listen 8443 ssl;
    listen [::]:8443 ssl;

    server_name 123.123.123.123;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols       TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:8000;
        include proxy_params;
    }
}
```

Replace `server_name` with your own server ip and `ssl_certificate`, 
`ssl_certificate_key` with real paths.

Add `client_max_body_size` to nginx.conf:

```
http {
        ...
        client_max_body_size 200M;
}
```

## Deployment

1. Deploy server and api proxy

```bash
docker compose up -d postgres tg_bot_api
```

2. Run migrations

```bash
docker compose up --build migrations
```

3. Deploy workers controller

```bash
docker compose up --build -d workers_controller clean_orders_queue
```

4. Run tests

```bash
docker compose up --build tests
```

5. Run bot

```bash
docker compose up --build -d bot
```

## Migrations

Create migration after changes in models
```bash
alembic revision --autogenerate -m "commit message"
```

Upgrade current database to latest version
```bash
alembic upgrade head
```

## Workers

Workers are containers that build the app. You can have multiple workers 
on different machines or a worker on the same machine with other 
containers.

At the development stage it is possible to mock build process instead 
of actually running them by setting the variable `MOCK_BUILD` to any 
*non-empty* value. In the mock mode it is possible to emulate build 
failure by setting the order's application ID to a string containing 
"error", e.g., `org.error.app`.

Send `/add_worker <name> [<ip>]` to the bot to obtain a WORKER_JWT. 
Send `/del_worker <name>` to delete a worker from the db.

#### Example of worker .env file (without real values). 

If you are running the worker from another machine, create a new .env file in 
the project root on that machine. If you run the worker on the machine with 
other containers, simply append the values to the existing .env.

```
DATA_DIR=./data
TMP_DIR=./data/tmp
MOCK_BUILD=False
WORKER_CONTROLLER_HOST=127.0.0.1:8000
WORKER_CHECK_INTERVAL_SEC=30
WORKER_JWT=CHANGE_ME
KEYSTORE_PASSWORD=CHANGE_ME
BUILD_DOCKER_IMAGE_NAME=masked-partisan-telegram-build
ALLOW_BUILD_SOURCES_ONLY=True
```

Copy the `cert.pem` from the worker controller to the `worker` dir. 

Generate RSA key for signing app signature:

```bash
openssl genrsa -out worker/private_key.pem
```

Run build worker:

```bash
docker compose up --build -d build_worker
```

#### Graceful shutdown

You can ask the worker to shut down after building current order. In this case 
if there is any running build it will not be interrupted. To do this run this
command:

```bash
docker compose kill -s SIGINT build_worker
```

## Containers description

`bot` - handles tg commands, sends apk files.

`clean_orders_queue` - removes completed tasks from db

`workers_controller` - web api used by workers.

`build_worker` - looks for prepared tasks and run build script to 
create an apk. The worker connects to the workers_controller. Uses 
docker-in-docker to compile apk. Second docker uses socket of host machine, 
so volume path must start from host machine path, not from current container 
path.

`postgres` - database.

`tg_bot_api` - local [api](https://hub.docker.com/r/aiogram/telegram-bot-api) for telegram bot. Allows sending files bigger 
than 20 MB.

`migrations` - run migrations before starting other containers.

`tests` - runs autotests.
