from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram import Bot, Dispatcher, F
from aiogram.types import Update
from aiogram.enums import ParseMode
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import redis.asyncio as redis
import secrets
import uvicorn
import os
from modules import router, Logger

logger = Logger(name="Main")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

if not BOT_TOKEN:
    raise ValueError("Bot token not set. Please configure TELEGRAM_BOT_TOKEN in your environment.")

# Generate or load webhook secret token
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")
if not WEBHOOK_SECRET:
    WEBHOOK_SECRET = secrets.token_urlsafe(32)
    logger.warning(f"Generated new webhook secret. Add to .env: TELEGRAM_WEBHOOK_SECRET={WEBHOOK_SECRET}")

# Initialize Redis storage for FSM
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    db=0,
    decode_responses=True,
)
storage = RedisStorage(redis_client, state_ttl=86400)  # 24 hour expiration

# Initialize bot and dispatcher with Redis storage
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)
dp.include_router(router)

# Add global middlewares
dp.callback_query.middleware(CallbackAnswerMiddleware(pre=True, text="🤔"))

# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    web_app_url = os.getenv("WEB_APP_URL")
    if not web_app_url:
        raise ValueError("WEB_APP_URL not set. Please configure WEB_APP_URL in your environment.")

    # Construct webhook URL from domain
    webhook_url = f"https://{web_app_url}/webhook"

    try:
        # Set webhook with secret token for security
        await bot.set_webhook(
            url=webhook_url,
            secret_token=WEBHOOK_SECRET,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )
        logger.info(f"Webhook successfully set to: {webhook_url} (with secret validation)")
        yield
    finally:
        await bot.delete_webhook()
        await redis_client.close()
        logger.info("Webhook deleted and Redis connection closed.")

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook(request: Request) -> JSONResponse:
    """Process Telegram webhook with signature validation."""
    # Validate secret token from header
    received_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")

    if received_secret != WEBHOOK_SECRET:
        logger.warning(
            f"Invalid webhook request from {request.client.host} - "
            f"Wrong secret token"
        )
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        json_data = await request.json()
        update = Update.model_validate(json_data, context={"bot": bot})
        logger.info(f"Webhook request received from {request.client.host}")
        await dp.feed_update(bot, update)
        return JSONResponse({"status": "ok"}, status_code=200)
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        # Return 200 to prevent Telegram retries on permanent errors
        return JSONResponse({"status": "error", "message": str(e)}, status_code=200)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5400,
        log_level="warning",  # Suppress Uvicorn logs
        access_log=False,     # Suppress request logs
    )