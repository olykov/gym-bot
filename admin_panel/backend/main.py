from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.v1 import router as api_v1_router
from app.api.v1 import user_router

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

app.include_router(api_v1_router.router, prefix=settings.API_V1_STR)
app.include_router(user_router.router, prefix=f"{settings.API_V1_STR}/user", tags=["user"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
