"""FastAPI application entry point for the Gym Tracker Core API.

Router mount order matters: FastAPI matches routes in registration order.
The bot-facing contract routers are mounted first so their paths win over the
legacy admin router on overlapping paths (e.g. GET /muscles, POST /exercises,
GET /training).

Router layout (GYM-22):
  /api/v1/...               — users, muscles, training  (bot_router.py)
  /api/v1/muscles/.../exer  — exercises                 (exercises_router.py)
  /api/v1/analytics/...     — analytics                 (analytics_router.py)
  /api/v1/...               — legacy admin/auth         (router.py)
  /api/v1/user/...          — legacy user training      (user_router.py)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.v1 import router as api_v1_router
from app.api.v1 import user_router
from app.api.v1 import bot_router
from app.api.v1 import exercises_router
from app.api.v1 import analytics_router

settings = get_settings()

app = FastAPI(title=settings.PROJECT_NAME)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bot-facing contract endpoints (GYM-22) — mounted first
app.include_router(bot_router.router, prefix=settings.API_V1_STR)
app.include_router(exercises_router.router, prefix=settings.API_V1_STR)
app.include_router(analytics_router.router, prefix=settings.API_V1_STR)

# Legacy admin/auth router (existing endpoints — untouched)
app.include_router(api_v1_router.router, prefix=settings.API_V1_STR)

# Legacy user training router
app.include_router(
    user_router.router,
    prefix=f"{settings.API_V1_STR}/user",
    tags=["user"],
)


@app.get("/health")
def health_check():
    """Liveness probe."""
    return {"status": "ok"}
