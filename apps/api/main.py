"""FastAPI application entry point for the Gym Tracker Core API.

Router mount order matters: FastAPI matches routes in registration order.
The bot-facing contract routers are mounted first so their paths win over the
legacy admin router on overlapping paths (e.g. GET /muscles, POST /exercises,
GET /training).

Router layout (GYM-22 + GYM-23):
  /api/v1/...               — users, muscles, training  (bot_router.py)
  /api/v1/muscles/.../exer  — exercises                 (exercises_router.py)
  /api/v1/analytics/...     — analytics                 (analytics_router.py)
  /api/v1/admin/...         — admin catalog + auth      (router.py)
  /api/v1/user/...          — legacy user training      (user_router.py)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.v1.router import router as api_v1_router, admin_router
from app.api.v1 import user_router
from app.api.v1 import bot_router
from app.api.v1 import exercises_router
from app.api.v1 import analytics_router

settings = get_settings()

app = FastAPI(title=settings.PROJECT_NAME)

# CORS — allow_origins sourced from CORS_ALLOW_ORIGINS env var (comma-separated).
# "*" is intentionally not used here because allow_credentials=True with "*"
# violates the CORS spec and is rejected by browsers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bot-facing contract endpoints (GYM-22) — mounted first
app.include_router(bot_router.router, prefix=settings.API_V1_STR)
app.include_router(exercises_router.router, prefix=settings.API_V1_STR)
app.include_router(analytics_router.router, prefix=settings.API_V1_STR)

# Auth and static-data endpoints — paths unchanged from pre-GYM-23.
app.include_router(api_v1_router, prefix=settings.API_V1_STR)

# Admin catalog endpoints — moved to /admin/* prefix (GYM-23).
# All routes require_admin. Eliminates path collisions with user-facing GYM-22 routers.
app.include_router(admin_router, prefix=f"{settings.API_V1_STR}/admin")

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
