"""
Chat Automation (Business) xabarlar uchun handlerlar.
Foydalanuvchining profilinga ulangan bot orqali kelgan xabarlarni qayta ishlash.
"""

import logging
from aiogram import Router, types
from database import db
from ai_providers import AIProvider
from locales import get_text

logger = logging.getLogger(__name__)
router = Router()


@router.business_connection()
async def business_connection_handler(event: types.BusinessConnection):
    """
    Business Connection hodisasi:
    - Foydalanuvchi profilingini botga ulaganda
    - Uzilganda
    """
    user_id = event.user.id
    connection_id = event.id

    user = db.get_user(user_id)
    if not user:
        # Foydalanuvchi bazada yo'q, qo'shamiz
        db.add_user(user_id, "uz")
        user = db.get_user(user_id)
    
    lang = user.get("language", "uz") if user else "uz"

    try:
        if event.is_enabled:
            # Ulanish yoqilgan
            logger.info(f"Foydalanuvchi {user_id} business connection yoqdi: {connection_id}")
            db.save_business_connection(user_id, connection_id)
            
            try:
                await event.bot.send_message(
                    user_id,
                    get_text(lang, "business_connected"),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Foydalanuvchi {user_id} ga xabar yuborib bo'lmadi: {e}")
        else:
            # Ulanish o'chirilgan
            logger.info(f"Foydalanuvchi {user_id} business connection o'chirdi: {connection_id}")
            db.remove_business_connection(user_id)
            
            try:
                await event.bot.send_message(
                    user_id,
                    get_text(lang, "business_disconnected"),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Foydalanuvchi {user_id} ga xabar yuborib bo'lmadi: {e}")
    except Exception as e:
        logger.error(f"Business connection handler xatolik: {e}", exc_info=True)


# Fayl boshiga import qo'shing
from ai_providers import AIProvider

# business_message_handler ichidagi AI qismini almashtiring
@router.business_message()
async def business_message_handler(message: types.Message):
    """Business orqali kelgan xabarlarni qayta ishlash."""
    try:
        business_connection_id = message.business_connection_id
        if not business_connection_id:
            return

        owner = db.get_user_by_business_connection(business_connection_id)
        if not owner:
            return

        user_id = owner["user_id"]
        lang = owner.get("language", "uz")

        if owner.get("bot_status") != "active":
            return

        message_text = message.text or message.caption or ""
        if not message_text.strip():
            return

        # 1. Avto-javoblar
        auto_reply = db.find_matching_reply(user_id, message_text)
        if auto_reply:
            try:
                await message.reply_text(auto_reply, parse_mode="HTML")
                return
            except Exception as e:
                logger.error(f"Avto-javob yuborishda xatolik: {e}")

        # 2. AI javoblar
        ai_settings = db.get_ai_settings(user_id)
        if ai_settings and ai_settings.get("is_active") and ai_settings.get("api_key"):
            provider = ai_settings.get("provider", "openai")
            api_key = ai_settings["api_key"]
            system_prompt = ai_settings.get("system_prompt", "")
            model = ai_settings.get("model_name")
            
            # AI dan javob olish
            result = await AIProvider.send_request(
                provider=provider,
                api_key=api_key,
                message=message_text,
                system_prompt=system_prompt,
                model=model
            )
            
            if result["success"]:
                try:
                    await message.reply_text(result["reply"][:4000], parse_mode="HTML")
                    logger.info(f"AI javob yuborildi: provider={provider}, user={user_id}")
                except Exception as e:
                    logger.error(f"AI javob yuborishda xatolik: {e}")
            else:
                logger.error(f"AI xatolik: {result['error']}")
                # AI ishlamasa, avto-javob topilmadi, jim turamiz

    except Exception as e:
        logger.error(f"Business message handler xatolik: {e}", exc_info=True)