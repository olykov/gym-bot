import asyncio
from aiogram import Bot, Dispatcher
from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from modules import router, Logger
from fastapi import FastAPI, Request
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os

logger = Logger(name="Main")
app = FastAPI()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Bot token not set. Please configure TELEGRAM_BOT_TOKEN in your environment.")

@app.post("/")
async def webhook(request: Request):
    try:
        json_data = await request.json()
        logger.info(f"Webhook request received from {request.client.host}: {json_data}")
        return JSONResponse(content={"status": 200, "message": "ok"}, status_code=200)
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return JSONResponse(content={"status": 500, "message": str(e)}, status_code=500)

async def start_polling():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    dp.callback_query.middleware(CallbackAnswerMiddleware(pre=True, text="🤔"))
    await dp.start_polling(bot)

async def run_fastapi():
    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=5400, log_level="warning", access_log=False,)
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    await asyncio.gather(start_polling(), run_fastapi())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped.")