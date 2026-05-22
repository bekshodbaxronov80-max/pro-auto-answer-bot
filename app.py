import os, sys, asyncio, threading, logging
from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from handlers import private, business

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Pro Auto Answer Bot - Online"

@app.route('/health')
def health():
    return "OK", 200

async def start_bot():
    from config import BOT_TOKEN
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(private.router)
    dp.include_router(business.router)
    
    @dp.errors()
    async def error_handler(event):
        logger.error(f"Xatolik: {event.exception}")
        return True
    
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Bot ishga tushdi!")
    await dp.start_polling(bot)

def run_bot():
    asyncio.run(start_bot())

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)