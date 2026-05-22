"""
Hosting uchun asosiy fayl.
Barcha hosting platformalarida ishlaydi.
"""

import os
import sys
import asyncio
import threading
import logging
from flask import Flask

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Pro Auto Answer Bot - Online", 200

@app.route('/health')
def health():
    return "OK", 200

# Bot funksiyasi
async def start_bot():
    from config import BOT_TOKEN
    from aiogram import Bot, Dispatcher
    from aiogram.enums import ParseMode
    from handlers import private, business
    
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN topilmadi!")
        return
    
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(private.router)
    dp.include_router(business.router)
    
    @dp.errors()
    async def error_handler(event):
        logger.error(f"Xatolik: {event.exception}")
        return True
    
    try:
        logger.info("✅ Bot ishga tushdi!")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot xatolik: {e}")

def run_bot():
    try:
        asyncio.run(start_bot())
    except Exception as e:
        logger.error(f"Thread xatolik: {e}")

# Botni backgroundda ishga tushirish
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)