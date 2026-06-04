"""Thin sync Redis cache helper for analytics endpoints (GYM-39).

Key shape: ``analytics:{user_id}:{endpoint}:{sorted_params}``
TTL:       90 seconds (short enough to feel live; long enough to absorb bursts).
DB index:  /1  (separates analytics cache from bot FSM on /0).

Design choices:
- Uses the ``redis`` library (sync) — consistent with the rest of the API which
  is synchronous (psycopg2 on the event loop, HP-1 open).
- Graceful degradation: any Redis error is caught, logged, and the caller falls
  through to the DB query.  A cache failure NEVER fails the HTTP request.
- The ``user_id`` is always the effective principal id (derived from get_principal)
  so users never share a cache entry — even if they request the same params.
"""
import json
import logging
from typing import Any, Optional

import redis as redis_lib

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_CACHE_TTL = 90  # seconds


def _get_client() -> Optional[redis_lib.Redis]:
    """Return a Redis client connected to REDIS_URL, or None on failure.

    Returns:
        A ``redis.Redis`` instance, or ``None`` if the connection cannot be
        established.  The caller treats ``None`` as a cache miss.
    """
    try:
        settings = get_settings()
        return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception as exc:
        logger.warning("cache: failed to create Redis client: %s", exc)
        return None


def make_key(user_id: int, endpoint: str, **params: Any) -> str:
    """Build a deterministic cache key for an analytics result.

    Params are sorted so that ``?a=1&b=2`` and ``?b=2&a=1`` map to the same key.

    Args:
        user_id: Effective principal id — ensures per-user isolation.
        endpoint: Short endpoint name, e.g. ``"activity"``, ``"summary"``.
        **params: Query parameters to include in the key.

    Returns:
        Cache key string.
    """
    sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return f"analytics:{user_id}:{endpoint}:{sorted_params}"


def cache_get(key: str) -> Optional[Any]:
    """Fetch a JSON value from the cache.

    Args:
        key: Cache key produced by ``make_key``.

    Returns:
        Deserialized Python value, or ``None`` on miss or Redis error.
    """
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning("cache_get(%r) failed: %s", key, exc)
        return None
    finally:
        try:
            client.close()
        except Exception:
            pass


def cache_set(key: str, value: Any, ttl: int = _CACHE_TTL) -> None:
    """Store a JSON-serialisable value in the cache with a TTL.

    Any error is swallowed — the caller's DB result has already been computed
    and must be returned regardless.

    Args:
        key: Cache key produced by ``make_key``.
        value: JSON-serialisable value to store.
        ttl: Time-to-live in seconds (default 90).
    """
    client = _get_client()
    if client is None:
        return
    try:
        client.set(key, json.dumps(value), ex=ttl)
    except Exception as exc:
        logger.warning("cache_set(%r) failed: %s", key, exc)
    finally:
        try:
            client.close()
        except Exception:
            pass
