"""Gym Tracker Core API client: async httpx wrapper + generated pydantic models.

Import the client and models from the package root::

    from gym_api_client import GymApiClient, models
"""

from __future__ import annotations

from . import models
from .client import (
    ACT_AS_USER_HEADER,
    SERVICE_TOKEN_HEADER,
    GymApiClient,
)

__all__ = [
    "GymApiClient",
    "models",
    "SERVICE_TOKEN_HEADER",
    "ACT_AS_USER_HEADER",
]
