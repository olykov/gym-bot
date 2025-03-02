from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram import Bot, Dispatcher, F
from aiogram.types import Update
from aiogram.enums import ParseMode
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import uvicorn
import os
from modules import router, Logger

logger = Logger(name="Main")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Bot token not set. Please configure TELEGRAM_BOT_TOKEN in your environment.")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(router)

# Add global middlewares
dp.callback_query.middleware(CallbackAnswerMiddleware(pre=True, text="🤔"))

# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    webhook_url = "https://2f49-149-3-86-53.ngrok-free.app/webhook"
    try:
        await bot.set_webhook(
            url=webhook_url,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )
        logger.info("Webhook successfully set.")
        yield
    finally:
        await bot.delete_webhook()
        logger.info("Webhook successfully deleted.")

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook(request: Request) -> None:
    # print(request.client)
    try:
        json_data = await request.json()
        update = Update.model_validate(json_data, context={"bot": bot})
        logger.info(f"Webhook request received from {request.client.host}")
        await dp.feed_update(bot, update)
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5400,
        log_level="warning",  # Suppress Uvicorn logs
        access_log=False,     # Suppress request logs
    )