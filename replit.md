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
      config.py          # Pydantic settings with auto URL resolution
      database.py        # Lazy async SQLAlchemy engine + Base
      redis_client.py    # redis.asyncio client with FakeRedis fallback
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
render.yaml              # Render IaC (web service + worker + postgres)
.env.example             # Environment variable template
requirements.txt         # Python dependencies
run_backend.py           # Local dev entry point
```

## Tech Stack

- **Python 3.11+**
- **aiogram 3.x** – Telegram bot
- **FastAPI** – REST API backend
- **SQLAlchemy (async)** – ORM
- **SQLite** (local dev) / **PostgreSQL** (Docker/Render production)
- **FakeRedis** (local dev) / **Redis via redis.asyncio** (Upstash/production)
- **Docker Compose** – full containerized local deployment
- **Render** – cloud deployment target

## Local Development (Replit)

The API runs on port **5000** using SQLite + Upstash Redis (BOT_TOKEN and REDIS_URL are in Secrets).

### Start the API
The workflow `LingoGenBot API` runs automatically. Visit `/docs` to explore the interactive API.

### To run the bot locally
```bash
python -m backend.bot.bot
```
Requires BOT_TOKEN to be set and the API to be reachable at BACKEND_URL.

## Render Deployment

### What gets deployed
| Service | Type | Description |
|---|---|---|
| `lingogenbot-api` | Web Service | FastAPI backend |
| `lingogenbot-bot` | Background Worker | aiogram Telegram bot |
| `lingogenbot-db` | PostgreSQL | Managed database (free tier) |

### Steps
1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → Blueprint
3. Connect your GitHub repo
4. Render will read `render.yaml` and create all three services automatically
5. In the Render dashboard, set these two secrets for **both** services:
   - `BOT_TOKEN` — your Telegram bot token from @BotFather
   - `REDIS_URL` — your Upstash Redis URL (e.g. `rediss://default:...@host.upstash.io:6379`)
6. After deploy, copy the API's public URL (e.g. `https://lingogenbot-api.onrender.com`)
7. Set `BACKEND_URL` on the **bot worker** service to that URL
8. Redeploy the bot worker

### Environment Variables (Render sets automatically)
| Variable | Source |
|---|---|
| `DATABASE_URL` | Auto-injected from linked Postgres database |
| `PORT` | Auto-injected by Render for web services |

### Environment Variables (you set manually in Render dashboard)
| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | Yes | Telegram bot token |
| `REDIS_URL` | Yes | Upstash Redis URL (`rediss://...`) |
| `BACKEND_URL` | Yes (bot only) | Public URL of the API service |
| `MONITOR_CHANNEL_ID` | No | Telegram channel ID for error alerts |

## Configuration Notes

- `APP_DATABASE_URL` is used in local dev (Replit) to avoid conflict with Replit's managed `DATABASE_URL`
- On Render, `DATABASE_URL` is auto-detected and converted to `postgresql+asyncpg://` format
- `REDIS_URL` starting with `redis://` is auto-upgraded to `rediss://` for Upstash/cloud providers
- If `REDIS_URL` contains a full `redis-cli` command, the actual URL is extracted automatically

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/users/register` | Register/update a user by telegram_id |
| GET  | `/api/v1/users/{telegram_id}` | Fetch user details |
| POST | `/api/v1/matchmaking/request` | Request a match |
| POST | `/api/v1/matchmaking/cancel` | Cancel active search |
| POST | `/api/v1/matchmaking/end-session` | End an active session |
| GET  | `/api/v1/matchmaking/session/{telegram_id}` | Get active session for user |
| GET  | `/api/v1/matchmaking/partner/{session_uuid}/{telegram_id}` | Get partner ID |
| GET  | `/api/v1/sessions/{session_uuid}` | Get session details |
| POST | `/api/v1/sessions/rating` | Submit a 1–5 rating |
| GET  | `/api/v1/sessions/{session_uuid}/ratings` | Get all ratings for a session |

## Docker (self-hosted)

```bash
cp .env.example .env
# Fill in BOT_TOKEN, REDIS_URL, and Postgres credentials
docker compose up -d
```
