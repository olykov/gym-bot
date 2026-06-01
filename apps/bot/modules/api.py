"""Shared async GymApiClient instance built from environment variables.

The client uses serviceAuth: X-Service-Token set at construction time,
and X-Act-As-User supplied per request via act_as_user=<telegram_id>.
"""

from __future__ import annotations

import os

from gym_api_client import GymApiClient

_API_BASE_URL: str = os.environ.get("API_BASE_URL", "http://admin_backend:8000/api/v1")
_BOT_SERVICE_TOKEN: str = os.environ.get("BOT_SERVICE_TOKEN", "")

# Single shared client; the underlying httpx.AsyncClient is connection-pooled.
api: GymApiClient = GymApiClient(
    base_url=_API_BASE_URL,
    service_token=_BOT_SERVICE_TOKEN,
)

__all__ = ["api"]
