from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request, status

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore


@dataclass(frozen=True)
class RateLimitConfig:
    window_seconds: int = 900  # 15 minutes
    max_attempts: int = 8      # 8 tries per window
    redis_url: str = "redis://localhost:6379/0"


def get_rate_limit_config() -> RateLimitConfig:
    return RateLimitConfig(
        window_seconds=int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "900")),
        max_attempts=int(os.getenv("AUTH_RATE_LIMIT_MAX_ATTEMPTS", "8")),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    )


def _redis_client(cfg: RateLimitConfig):
    if redis is None:
        raise RuntimeError(
            "redis package is not installed. Run: poetry add redis"
        )
    return redis.Redis.from_url(cfg.redis_url, decode_responses=True)


def _client_ip(request: Request) -> str:
    # Works with proxies/load balancers if you set trusted proxy correctly upstream.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _hash_identifier(identifier: str) -> str:
    return hashlib.sha256(identifier.strip().lower().encode("utf-8")).hexdigest()


def _key(request: Request, identifier: str) -> str:
    ip = _client_ip(request)
    return f"rl:auth:{ip}:{_hash_identifier(identifier)}"


def _too_many(retry_after_seconds: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many login attempts. Please try again later.",
        headers={"Retry-After": str(retry_after_seconds)},
    )


def check_auth_rate_limit(request: Request, identifier: str) -> None:
    """
    Call BEFORE verifying password.
    Uses a fixed-window counter in Redis keyed by IP + identifier hash.
    """
    cfg = get_rate_limit_config()
    r = _redis_client(cfg)
    key = _key(request, identifier)

    count = r.incr(key)
    if count == 1:
        r.expire(key, cfg.window_seconds)

    if count > cfg.max_attempts:
        ttl = r.ttl(key)
        retry_after = ttl if isinstance(ttl, int) and ttl > 0 else cfg.window_seconds
        raise _too_many(retry_after_seconds=retry_after)


def reset_auth_rate_limit(request: Request, identifier: str) -> None:
    """
    Optional: call on successful login to clear failures for that IP+identifier.
    """
    cfg = get_rate_limit_config()
    r = _redis_client(cfg)
    r.delete(_key(request, identifier))