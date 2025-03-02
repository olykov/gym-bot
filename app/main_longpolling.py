import asyncio
from aiogram import Bot, Dispatcher
from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from modules import router
import os

async def main():
    bot = Bot(token=os.environ.get("TELEGRAM_BOT_TOKEN"))
    dp = Dispatcher()
    dp.include_router(router)
    dp.callback_query.middleware(CallbackAnswerMiddleware(pre=True, text="🤔"))
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
