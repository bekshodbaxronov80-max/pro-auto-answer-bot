"""
Render.com uchun moslashtirilgan asosiy fayl.
Flask (port ochish uchun) + Aiogram polling.
"""

import os
import asyncio
import threading
import logging
from flask import Flask

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Flask ilova (Render port ochish uchun kerak)
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot ishlamoqda!", 200

@app.route('/health')
def health():
    return "OK", 200

# Bot funksiyasi
async def main():
    """Botni ishga tushiruvchi asosiy funksiya."""
    try:
        from config import BOT_TOKEN
        from aiogram import Bot, Dispatcher
        from aiogram.enums import ParseMode
        from handlers import private, business

        logger.info(f"Token topildi: {BOT_TOKEN[:10]}...")
        
        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN topilmadi!")
            return

        bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
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
    """Botni alohida threadda ishga tushirish."""
    asyncio.run(main())

# Botni backgroundda ishga tushirish
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Server {port} portda ishga tushmoqda...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)