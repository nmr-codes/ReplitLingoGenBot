# LingoGenBot

A production-ready MVP backend for a Telegram bot that connects users anonymously to practice English via real-time text chat.

## Architecture

```
backend/
  app/
    main.py              # FastAPI application entry point with lifespan management
    api/
      routers/
        users.py         # User registration & lookup
        matchmaking.py   # Partner search, session start/end
        sessions.py      # Session details & rating submission
    services/
      user_service.py    # User CRUD logic
      matchmaking_service.py  # Redis queue, session creation
      session_service.py      # Session queries, rating storage
      topics.py          # 24 predefined conversation topics
    models/
      user.py            # User ORM model (telegram_id as PK)
      session.py         # Session ORM model (session_uuid as PK)
      rating.py          # Rating ORM model
    core/
      config.py          # Pydantic settings (APP_DATABASE_URL priority)
      database.py        # Lazy async SQLAlchemy engine + Base
      redis_client.py    # Redis/FakeRedis queue and state helpers
      logging_config.py  # File + stdout logging setup
  bot/
    bot.py               # aiogram Dispatcher setup + polling
    monitoring.py        # Telegram monitoring channel alerts
    handlers/
      start.py           # /start command, main keyboard
      matchmaking.py     # Find Partner flow with live GIF countdown
      session.py         # End Session + inline rating keyboard
      messaging.py       # Anonymous message relay between partners
docker-compose.yml       # Postgres + Redis + backend + bot containers
Dockerfile.backend       # FastAPI container
Dockerfile.bot           # aiogram bot container
.env.example             # Environment variable template
requirements.txt         # Python dependencies
run_backend.py           # Local dev entry point
```

## Tech Stack

- **Python 3.11+**
- **aiogram 3.x** – Telegram bot
- **FastAPI** – REST API backend
- **SQLAlchemy (async)** – ORM
- **SQLite** (local dev) / **PostgreSQL** (Docker/production)
- **FakeRedis** (local dev) / **Redis** (Docker/production)
- **Docker Compose** – full containerized deployment

## Local Development (Replit)

The API runs on port **5000** using SQLite + FakeRedis (no Docker needed).

### Start the API
The workflow `LingoGenBot API` runs automatically. Visit `/docs` to explore the interactive API.

### Environment Variables
| Variable | Description | Default |
|---|---|---|
| `APP_DATABASE_URL` | Override DB URL (SQLite or PostgreSQL+asyncpg) | `sqlite+aiosqlite:///./lingogenbot.db` |
| `REDIS_URL` | Redis URL (`fakeredis://` for local) | `fakeredis://` |
| `BOT_TOKEN` | Telegram bot token (required for bot) | - |
| `MONITOR_CHANNEL_ID` | Telegram channel ID for error alerts | - |
| `BACKEND_URL` | URL bot uses to reach the API | `http://localhost:8000` |
| `MATCH_TIMEOUT_SECONDS` | Max wait time in matchmaking queue | `120` |
| `SESSION_DURATION_SECONDS` | Chat session length | `300` |
| `SEARCH_UPDATE_INTERVAL` | Caption refresh interval in seconds | `15` |

## Docker Deployment

```bash
cp .env.example .env
# Edit .env with your BOT_TOKEN and other secrets
docker compose up -d
```

This starts:
- `postgres` on port 5432
- `redis` on port 6379
- `backend` (FastAPI) on port 8000
- `bot` (aiogram polling)

For production use `postgresql+asyncpg://...` in `DATABASE_URL` and a real Redis URL.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/users/register` | Register/update a user by telegram_id |
| GET  | `/api/v1/users/{telegram_id}` | Fetch user details |
| POST | `/api/v1/matchmaking/request` | Request a match (enqueues or immediately pairs) |
| POST | `/api/v1/matchmaking/cancel` | Cancel active search |
| POST | `/api/v1/matchmaking/end-session` | End an active session |
| GET  | `/api/v1/matchmaking/session/{telegram_id}` | Get active session for user |
| GET  | `/api/v1/matchmaking/partner/{session_uuid}/{telegram_id}` | Get partner ID |
| GET  | `/api/v1/sessions/{session_uuid}` | Get session details |
| POST | `/api/v1/sessions/rating` | Submit a 1–5 rating |
| GET  | `/api/v1/sessions/{session_uuid}/ratings` | Get all ratings for a session |

## Bot Setup

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Set `BOT_TOKEN` as a secret in Replit (Secrets tab)
3. Run `python -m backend.bot.bot` (requires backend to be running at `BACKEND_URL`)

## Monitoring

Set `MONITOR_CHANNEL_ID` to a Telegram channel ID (e.g., `-100123456789`). The bot forwards INFO/WARNING/ERROR/CRITICAL events to that channel with timestamps and tracebacks.

## Key Design Decisions

- `telegram_id` is the primary key for `User` (no separate surrogate key needed)
- `session_uuid` (UUID4) is the primary key for `Session` (globally unique, no integer PK collision)
- FakeRedis is used transparently in dev; switching to real Redis requires only changing `REDIS_URL`
- `APP_DATABASE_URL` env var takes priority over Replit's managed `DATABASE_URL` to avoid conflicts
- All datetime arithmetic handles both tz-aware (PostgreSQL) and tz-naive (SQLite) returns gracefully
