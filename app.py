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

# ===== BOT NI ISHGA TUSHIRISH =====
def run_bot():
    try:
        from config import BOT_TOKEN
        logger.info(f"Token: {BOT_TOKEN[:15]}... (uzunligi: {len(BOT_TOKEN)})")
        
        if not BOT_TOKEN:
            logger.error("❌ TOKEN TOPILMADI!")
            return
        
        from aiogram import Bot, Dispatcher
        from aiogram.enums import ParseMode
        
        bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
        dp = Dispatcher()
        
        from handlers import private, business
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
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start())
        
    except Exception as e:
        logger.error(f"BOT XATOLIK: {e}")
        import traceback
        logger.error(traceback.format_exc())

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)