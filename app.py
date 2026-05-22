import os
import sys
import asyncio
import threading
import logging
from flask import Flask

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Online", 200

@app.route('/health')
def health():
    return "OK", 200

def run_bot():
    """Botni alohida threadda ishga tushirish"""
    try:
        from config import BOT_TOKEN
        from aiogram import Bot, Dispatcher
        from aiogram.enums import ParseMode
        from handlers import private, business
        
        logger.info(f"Token topildi: {BOT_TOKEN[:10]}...")
        
        bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
        dp = Dispatcher()
        dp.include_router(private.router)
        dp.include_router(business.router)
        
        @dp.errors()
        async def error_handler(event):
            logger.error(f"Xatolik: {event.exception}")
            return True
        
        async def start():
            logger.info("✅ Bot ishga tushdi!")
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
        
        asyncio.run(start())
        
    except Exception as e:
        logger.error(f"Bot xatolik: {e}")

# Botni darhol ishga tushirish
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)