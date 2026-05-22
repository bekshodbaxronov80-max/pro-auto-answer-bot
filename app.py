import os
import sys
import asyncio
import threading
import logging
import traceback
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
    try:
        from config import BOT_TOKEN
        logger.info(f"Token: {BOT_TOKEN[:15]}... (uzunligi: {len(BOT_TOKEN)})")
        
        if not BOT_TOKEN:
            logger.error("❌ TOKEN TOPILMADI!")
            return
        
        # Kutubxonalarni import qilishda xatolik bormi?
        logger.info("Import qilinyapti...")
        from aiogram import Bot, Dispatcher
        from aiogram.enums import ParseMode
        logger.info("aiogram import OK")
        
        from handlers import private, business
        logger.info("handlers import OK")
        
        from database import db
        logger.info("database import OK")
        
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
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start())
        
    except Exception as e:
        logger.error(f"❌ BOT XATOLIK: {e}")
        logger.error(traceback.format_exc())

# Botni darhol ishga tushirish (threadda emas, to'g'ridan-to'g'ri)
import time
time.sleep(2)
run_bot()