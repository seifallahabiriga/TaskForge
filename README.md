# TaskForge

**TaskForge** is a production-grade async AI task orchestration platform. Submit inference or analysis jobs via REST API — they're queued in Redis, picked up by Celery workers, routed through a multi-provider ML fallback chain (Groq → Gemini → HuggingFace → OpenRouter), and results stored in PostgreSQL with full audit logging.

[![CI](https://github.com/seifallahabiriga/taskforge/actions/workflows/ci.yaml/badge.svg)](https://github.com/seifallahabiriga/taskforge/actions/workflows/ci.yaml)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg?logo=docker&logoColor=white)](https://hub.docker.com/)
[![Image](https://img.shields.io/badge/ghcr.io-seifallahabiriga%2Ftaskforge-green.svg)](https://ghcr.io/seifallahabiriga/taskforge)

---

## Stack

| Layer | Technology |
|---|---|
| **API** | FastAPI + Uvicorn / Gunicorn |
| **Database** | PostgreSQL + SQLAlchemy (async) + Alembic |
| **Queue** | Celery + Redis |
| **ML Providers** | Groq → Gemini → HuggingFace → OpenRouter (fallback chain) |
| **Auth** | JWT (access + refresh tokens) + bcrypt |
| **Infra** | Docker + Docker Compose |

---

## Project Structure

```
taskforge/
├── .github/
│   └── workflows/
│       └── ci.yaml
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.dev.yml
│   └── docker-compose.prod.yml
├── backend/
│   ├── main.py
│   ├── api/
│   │   ├── deps.py
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── task.py
│   │       ├── execution.py
│   │       ├── result.py
│   │       ├── audit_log.py
│   │       └── user.py
│   ├── core/
│   │   ├── config.py
│   │   ├── enums.py
│   │   ├── exceptions.py
│   │   └── security.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── middleware/
│   │   └── rate_limiter.py
│   ├── ml/
│   │   ├── router.py
│   │   └── providers/
│   │       ├── base.py
│   │       ├── groq.py
│   │       ├── gemini.py
│   │       ├── huggingface.py
│   │       └── openrouter.py
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   ├── queue/
│   │   ├── celery_app.py
│   │   ├── producer.py
│   │   ├── tasks.py
│   │   └── redis_client.py
│   └── workers/
│       └── worker_app/
│           └── job_runner.py
├── alembic/
├── alembic.ini
├── requirements.txt
├── .dockerignore
└── .env.example
```

---

## Local Development

### Prerequisites

- Docker + Docker Compose
- API keys for at least one ML provider (Groq recommended — it's free and fast)

### Setup

```bash
git clone https://github.com/seifallahabiriga/taskforge.git
cd taskforge
cp .env.example .env   # fill in your values
docker compose -f docker/docker-compose.dev.yml up --build
```

- API: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`

### Running migrations manually

```bash
docker compose -f docker/docker-compose.dev.yml exec api alembic upgrade head
```

### Running the Celery worker

The dev compose starts the worker automatically. To restart it:

```bash
docker compose -f docker/docker-compose.dev.yml restart worker
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the required values. Here is a full reference:

```env
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=
POSTGRES_DB=taskforge
DATABASE_ASYNC_URL=postgresql+asyncpg://postgres:password@db:5432/taskforge
DATABASE_SYNC_URL=postgresql+psycopg2://postgres:password@db:5432/taskforge

# Redis / Celery
REDIS_URL=redis://:password@redis:6379/0
REDIS_PASSWORD=
CELERY_BROKER_URL=redis://:password@redis:6379/0
CELERY_RESULT_BACKEND=redis://:password@redis:6379/1
CELERY_DEFAULT_QUEUE=ai_default
CELERY_HIGH_PRIORITY_QUEUE=ai_high_priority
CELERY_LOW_PRIORITY_QUEUE=ai_low_priority
CELERY_MAX_RETRIES=3
CELERY_RETRY_DELAY_SECONDS=5

# Auth
SECRET_KEY=
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# App
APP_NAME=TaskForge
APP_URL=http://localhost:8000
ENVIRONMENT=development
DEBUG=false

# ML Providers (at least one required)
GROQ_API_KEY=
GEMINI_API_KEY=
HUGGINGFACE_API_KEY=
OPENROUTER_API_KEY=

# ML Settings
API_INFERENCE_TOKEN_LIMIT=1000
API_INFERENCE_TEMPERATURE=0.7
API_ANALYSIS_TOKEN_LIMIT=500
API_ANALYSIS_TEMPERATURE=0.2

# Rate Limits (requests per window)
RATE_LIMIT_AUTH_REGISTER=5
RATE_LIMIT_AUTH_LOGIN=10
RATE_LIMIT_TASK_CREATE=30
RATE_LIMIT_TASK_READ=120
RATE_LIMIT_DEFAULT=60
```

---

## API Reference

### Auth

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/auth/register` | Register new user, returns tokens | No |
| POST | `/auth/login` | Login, returns tokens | No |
| POST | `/auth/refresh` | Exchange refresh token for new access token | No |

### Tasks

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/tasks/` | Create and enqueue a task | User |
| GET | `/tasks/user/me` | List current user's tasks | User |
| GET | `/tasks/{task_id}` | Get task (owner only) | User |
| GET | `/tasks/{task_id}/status` | Poll task status | User |
| DELETE | `/tasks/{task_id}` | Delete task (owner only) | User |
| POST | `/tasks/{task_id}/start` | Force start | Admin |
| POST | `/tasks/{task_id}/complete` | Force complete | Admin |
| POST | `/tasks/{task_id}/fail` | Force fail | Admin |
| POST | `/tasks/{task_id}/retry` | Force retry | Admin |

### Results & Executions

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/results/{task_id}` | Get stored model output | User |
| GET | `/executions/{task_id}` | Get execution history | User |

### Audit (Admin only)

| Method | Endpoint |
|---|---|
| GET | `/audit/user/{user_id}` |
| GET | `/audit/entity/{entity_type}/{entity_id}` |
| GET | `/audit/action/{action}` |

### Monitoring

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | DB + Redis connectivity check |
| GET | `/metrics` | Prometheus-compatible metrics |

---

## Task Payload

**Request:**

```json
POST /tasks/
{
  "name": "my task",
  "task_type": "INFERENCE",
  "input_payload": {
    "prompt": "Explain async/await in one sentence."
  },
  "priority": 0,
  "model_version_id": null
}
```

**Field notes:**

| Field | Values | Description |
|---|---|---|
| `task_type` | `INFERENCE`, `ANALYSIS` | Determines which model and temperature settings are used |
| `priority` | `0` (default), `1` (high), `-1` (low) | Maps to the appropriate Celery queue |
| `model_version_id` | `null` or UUID | Reserved for pinning a specific model version; leave `null` to use the provider chain |

**Response:**

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "my task",
  "task_type": "INFERENCE",
  "status": "QUEUED",
  "priority": 0,
  "created_at": "2026-01-01T00:00:00Z"
}
```

---

## Task Lifecycle

```
PENDING → QUEUED → RUNNING → SUCCESS
                           → FAILED
                           → RETRYING → QUEUED
```

Illegal transitions are rejected with a `409 Conflict`.

---

## Dual Database Engine

TaskForge runs **two SQLAlchemy engines against the same PostgreSQL database**:

| Engine | Driver | Used by |
|---|---|---|
| `async_engine` (`asyncpg`) | `DATABASE_ASYNC_URL` | FastAPI request handlers |
| `sync_engine` (`psycopg2`) | `DATABASE_SYNC_URL` | Celery workers |

**Why?** FastAPI is fully async — it needs `asyncpg` to avoid blocking the event loop. Celery workers run in a standard synchronous process — `asyncio` event loops don't compose cleanly inside Celery tasks, so they get a plain `psycopg2` engine instead.

Both URLs point at the same database. The session factories (`AsyncSessionLocal` / `SyncSessionLocal`) are kept in `backend/db/session.py` and injected via FastAPI's dependency system (`get_async_db`) or called directly in worker code (`get_sync_db`).


---

## ML Provider Chain

Providers are tried in order until one succeeds. Each provider has its own model assignment — there is no shared request object passed between them.

| Priority | Provider | INFERENCE model | ANALYSIS model |
|---|---|---|---|
| 1 | Groq | `llama-3.1-8b-instant` | `llama-3.3-70b-versatile` |
| 2 | Gemini | `gemini-2.5-flash` | `gemini-2.5-flash` |
| 3 | HuggingFace | `Llama-3.1-8B-Instruct` | `Llama-3.1-8B-Instruct` |
| 4 | OpenRouter | `llama-3.2-3b-instruct:free` | `llama-3.2-3b-instruct:free` |

---

## Security Notes

- **Admin promotion is intentionally manual** — `is_admin` is never exposed in any input schema. To grant admin access:
  ```sql
  UPDATE users SET is_admin = true WHERE email = 'you@example.com';
  ```
- **Admin routes are silent on auth failures** — they return `403 Forbidden` with no detail about why, to avoid leaking role information.
- **Rate limiting** uses a Redis sliding window — per-IP for auth endpoints, per-user for all other routes.

---

## Running Tests

```bash
# Run all tests (no Celery worker needed)
pytest -m "not e2e" -v

# Run E2E tests (requires a running Celery worker + valid API keys)
pytest -m e2e -v
```

Tests use a separate `taskforge_test` database. Set `TEST_DATABASE_ASYNC_URL` in your environment before running locally.

---

## CI/CD

GitHub Actions pipeline (see [`.github/workflows/ci.yaml`](.github/workflows/ci.yaml)) runs on every push:

1. **lint** — `ruff`
2. **test** — `pytest` against real Postgres + Redis (Actions services)
3. **build** — `docker build`
4. **push** — to `ghcr.io` on `main` only, tagged `:latest` and `:{sha}`

```
ghcr.io/seifallahabiriga/taskforge:latest
```

---

## Roadmap

- [ ] WebSocket endpoint for real-time task status updates
- [ ] Frontend (Next.js)
- [ ] Worker registration (table exists, signals not wired up)
- [ ] Embeddings task type
- [ ] Cloud deployment (GCP / AWS)

---

## Contributing

Contributions are welcome. Please follow these guidelines:

1. Fork the repo and create a feature branch
2. Follow the existing code style — the project uses `ruff` for linting
3. Write or update tests for any changed behavior
4. Open a pull request with a clear description of what changed and why

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.