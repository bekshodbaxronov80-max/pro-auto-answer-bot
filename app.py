"""
Render.com uchun moslashtirilgan asosiy fayl.
aiogram 3.15.0 + Flask.
"""

import os
import sys
import asyncio
import threading
import logging
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot ishlamoqda!", 200

@app.route('/health')
def health():
    return "OK", 200

async def main():
    try:
        from config import BOT_TOKEN
        from aiogram import Bot, Dispatcher
        from aiogram.enums import ParseMode
        from aiogram.client.default import DefaultBotProperties
        import private
        import business

        logger.info(f"Token topildi: {BOT_TOKEN[:10]}...")

        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()

        dp.include_router(private.router)
        dp.include_router(business.router)

        logger.info("Handlerlar ulandi.")

        @dp.errors()
        async def error_handler(event):
            logger.error(f"Xatolik: {event.exception}")
            return True

        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Bot ishga tushdi!")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Bot xatolik: {e}")

def run_bot():
    asyncio.run(main())

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Server {port} portda ishga tushmoqda...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)