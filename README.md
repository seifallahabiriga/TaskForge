# TaskForge

Async AI task execution platform. Submit inference or analysis jobs via REST API — they're queued, picked up by Celery workers, routed through a multi-provider ML fallback chain, and results stored in PostgreSQL.

---

## Stack

- **API** — FastAPI + Uvicorn/Gunicorn
- **Database** — PostgreSQL + SQLAlchemy (async) + Alembic
- **Queue** — Celery + Redis
- **ML Providers** — Groq → Gemini → HuggingFace → OpenRouter (fallback chain)
- **Auth** — JWT (access + refresh tokens) + bcrypt
- **Infra** — Docker + Docker Compose

---

## Project Structure

```
taskforge/
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   └── .dockerignore
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
└── .env
```

---

## Local Development

### Prerequisites

- Docker + Docker Compose
- API keys for at least one ML provider (Groq recommended)

### Setup

```bash
git clone https://github.com/seifallahabiriga/taskforge.git
cd taskforge
cp .env.example .env   # fill in your values
docker compose -f docker/docker-compose.dev.yml up --build
```

API available at `http://localhost:8000`.  
Docs at `http://localhost:8000/docs`.

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

# ML Providers
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
| GET | `/health` | DB + Redis connectivity |
| GET | `/metrics` | Prometheus metrics |

---

## Task Payload

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

`task_type` is either `INFERENCE` or `ANALYSIS`.

---

## Task Lifecycle

```
PENDING → QUEUED → RUNNING → SUCCESS
                           → FAILED
                           → RETRYING → QUEUED
```

Illegal transitions are rejected with a 409.

---

## ML Provider Chain

Providers are tried in order. Each gets its own model ID — no shared request object.

| Priority | Provider | INFERENCE model | ANALYSIS model |
|---|---|---|---|
| 1 | Groq | llama-3.1-8b-instant | llama-3.3-70b-versatile |
| 2 | Gemini | gemini-2.5-flash | gemini-2.5-flash |
| 3 | HuggingFace | Llama-3.1-8B-Instruct | Llama-3.1-8B-Instruct |
| 4 | OpenRouter | llama-3.2-3b-instruct:free | llama-3.2-3b-instruct:free |

---

## Security Notes

- `is_admin` is never exposed in any input schema. To make a user admin: `UPDATE users SET is_admin = true WHERE email = '...'`
- Admin routes return `403 Forbidden.` with no detail about why
- Rate limiting uses Redis sliding window, per-IP for auth endpoints, per-user for everything else

---

## Running Tests

```bash
# Run all tests except E2E (no Celery worker needed)
pytest -m "not e2e" -v

# Run E2E tests (requires running Celery worker + real API keys)
pytest -m e2e -v
```

Tests use a separate `taskforge_test` database. Set `TEST_DATABASE_ASYNC_URL` in your environment before running locally.

---

## CI/CD

GitHub Actions pipeline on every push:

1. **lint** — ruff
2. **test** — pytest against real Postgres + Redis (Actions services)
3. **build** — `docker build`
4. **push** — to `ghcr.io` on `main` only, tagged `:latest` and `:{sha}`

Image: `ghcr.io/seifallahabiriga/taskforge:latest`

---

## What's Not Done Yet

- Cloud deployment
- WebSocket endpoint for real-time task status
- Frontend (Next.js)
- Worker registration (table exists, signals not wired up)
- Embeddings task type