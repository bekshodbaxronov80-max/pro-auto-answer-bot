"""
'Telegram Bot Free Hosting' ilovasi uchun moslashtirilgan asosiy fayl.
Botni webhook orqali emas, polling bilan ishga tushiradi.
"""

import asyncio
import logging

# Logging sozlamalari
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def main():
    """Botni ishga tushiruvchi asosiy funksiya."""
    try:
        # 1. Kerakli modullarni import qilish
        from config import BOT_TOKEN
        from aiogram import Bot, Dispatcher
        from aiogram.enums import ParseMode
        from handlers import private, business
        
        # 2. Tokenni tekshirish
        logger.info(f"Bot tokeni topildi: {BOT_TOKEN[:10]}...")
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN topilmadi!")
            return

        # 3. Bot va Dispatcher obyektlarini yaratish
        bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
        dp = Dispatcher()
        
        # 4. Handlerlarni ulash
        dp.include_router(private.router)
        dp.include_router(business.router)
        logger.info("Handlerlar muvaffaqiyatli ulandi.")

        # 5. Xatoliklarni ushlash
        @dp.errors()
        async def error_handler(event):
            logger.error(f"Xatolik yuz berdi: {event.exception}")
            return True

        # 6. Eski webhook'ni o'chirib, polling'ni boshlash
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Bot muvaffaqiyatli ishga tushdi! Polling boshlandi...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Botni ishga tushirishda xatolik: {e}")

if __name__ == "__main__":
    logger.info("Dastur ishga tushirilmoqda...")
    asyncio.run(main())