import time
import redis.asyncio as aioredis

from fastapi import Request, HTTPException, status

from backend.core.config import settings


# ------------------------------------------------------------------ #
# Redis connection                                                     #
# ------------------------------------------------------------------ #

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


# ------------------------------------------------------------------ #
# Core sliding window counter                                         #
# ------------------------------------------------------------------ #

async def _check_rate_limit(
    key: str,
    limit: int,
    window_seconds: int,
) -> tuple[bool, int]:
    """
    Sliding window rate limit using Redis.
    Returns (allowed: bool, retry_after_seconds: int).

    Key format: rl:{scope}:{identifier}
    Uses a simple counter with TTL — increments on each request,
    sets TTL on first request in the window.
    """
    r = get_redis()
    current = await r.get(key)

    if current is None:
        await r.set(key, 1, ex=window_seconds)
        return True, 0

    count = int(current)
    if count >= limit:
        ttl = await r.ttl(key)
        return False, max(ttl, 1)

    await r.incr(key)
    return True, 0


def _raise_429(retry_after: int):
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded. Try again later.",
        headers={"Retry-After": str(retry_after)},
    )


# ------------------------------------------------------------------ #
# Public rate limit dependencies                                      #
# ------------------------------------------------------------------ #

async def limit_auth_register(request: Request):
    """n register attempts per hour per IP."""
    ip = _get_ip(request)
    key = f"rl:auth:register:{ip}"
    allowed, retry_after = await _check_rate_limit(
        key,
        limit=settings.RATE_LIMIT_AUTH_REGISTER,
        window_seconds=3600,
    )
    if not allowed:
        _raise_429(retry_after)


async def limit_auth_login(request: Request):
    """n login attempts per 15 minutes per IP."""
    ip = _get_ip(request)
    key = f"rl:auth:login:{ip}"
    allowed, retry_after = await _check_rate_limit(
        key,
        limit=settings.RATE_LIMIT_AUTH_LOGIN,
        window_seconds=900,
    )
    if not allowed:
        _raise_429(retry_after)


async def limit_task_create(request: Request):
    """n task submissions per hour per user."""
    user_id = _get_user_id(request)
    key = f"rl:task:create:{user_id}"
    allowed, retry_after = await _check_rate_limit(
        key,
        limit=settings.RATE_LIMIT_TASK_CREATE,
        window_seconds=3600,
    )
    if not allowed:
        _raise_429(retry_after)


async def limit_task_read(request: Request):
    """n read requests per hour per user."""
    user_id = _get_user_id(request)
    key = f"rl:task:read:{user_id}"
    allowed, retry_after = await _check_rate_limit(
        key,
        limit=settings.RATE_LIMIT_TASK_READ,
        window_seconds=3600,
    )
    if not allowed:
        _raise_429(retry_after)


async def limit_default(request: Request):
    """n requests per hour per user — applied to everything else."""
    user_id = _get_user_id(request)
    key = f"rl:default:{user_id}"
    allowed, retry_after = await _check_rate_limit(
        key,
        limit=settings.RATE_LIMIT_DEFAULT,
        window_seconds=3600,
    )
    if not allowed:
        _raise_429(retry_after)


# ------------------------------------------------------------------ #
# Internal helpers                                                    #
# ------------------------------------------------------------------ #

def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_user_id(request: Request) -> str:
    """
    Extracts user_id from request state — set by get_current_user dep.
    Falls back to IP if not authenticated (should not happen on
    authenticated routes but safe to handle).
    """
    user = getattr(request.state, "current_user", None)
    if user:
        return str(user.id)
    return _get_ip(request)