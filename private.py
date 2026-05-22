"""
Botning o'ziga keladigan shaxsiy xabarlar uchun handlerlar.
/start, til tanlash, menyular va sozlamalar.
"""

from aiogram import Router, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import db
from ai_providers import AIProvider
from locales import LANGUAGES, get_text
import re
import aiohttp
router = Router()


class UserStates(StatesGroup):
    """Foydalanuvchi holatlari."""
    waiting_for_language = State()
    waiting_for_reply = State()
    waiting_for_delete_id = State()
    waiting_for_ai_api_key = State()
    waiting_for_ai_prompt = State()
    waiting_for_ai_settings = State()
      

# API kalit formatlarini tekshirish uchun patternlar
API_KEY_PATTERNS = {
    "openai": {
        "pattern": r"^sk-(proj-)?[A-Za-z0-9_-]+$",
        "prefix": "sk-",
        "min_length": 20,
        "description": "sk-... yoki sk-proj-... bilan boshlanadi",
        "test_endpoint": "https://api.openai.com/v1/models",
        "test_header": lambda key: {"Authorization": f"Bearer {key}"}
    },
    "claude": {
        "pattern": r"^sk-ant-[A-Za-z0-9_-]+$",
        "prefix": "sk-ant-",
        "min_length": 30,
        "description": "sk-ant-... bilan boshlanadi",
        "test_endpoint": "https://api.anthropic.com/v1/messages",
        "test_header": lambda key: {"x-api-key": key, "anthropic-version": "2023-06-01"}
    },
    "gemini": {
        "pattern": r"^AIza[0-9A-Za-z_-]{35}$",
        "prefix": "AIza",
        "min_length": 39,
        "description": "AIza... bilan boshlanadi, 39 ta belgi",
        "test_endpoint": "https://generativelanguage.googleapis.com/v1beta/models?key=",
        "test_header": lambda key: {}
    },
    "deepseek": {
        "pattern": r"^sk-[A-Za-z0-9]+$",
        "prefix": "sk-",
        "min_length": 20,
        "description": "sk-... bilan boshlanadi",
        "test_endpoint": "https://api.deepseek.com/v1/models",
        "test_header": lambda key: {"Authorization": f"Bearer {key}"}
    },
    "mistral": {
        "pattern": r"^[A-Za-z0-9]+$",
        "prefix": "",
        "min_length": 20,
        "description": "Harf va raqamlardan iborat",
        "test_endpoint": "https://api.mistral.ai/v1/models",
        "test_header": lambda key: {"Authorization": f"Bearer {key}"}
    },
    "llama": {
        "pattern": r"^gsk_[A-Za-z0-9]+$",
        "prefix": "gsk_",
        "min_length": 30,
        "description": "gsk_... bilan boshlanadi (Groq API)",
        "test_endpoint": "https://api.groq.com/openai/v1/models",
        "test_header": lambda key: {"Authorization": f"Bearer {key}"}
    },
    "cohere": {
        "pattern": r"^[A-Za-z0-9]+$",
        "prefix": "",
        "min_length": 20,
        "description": "Harf va raqamlardan iborat",
        "test_endpoint": "https://api.cohere.ai/v1/check-api-key",
        "test_header": lambda key: {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    },
    "grok": {
        "pattern": r"^xai-[A-Za-z0-9]+$",
        "prefix": "xai-",
        "min_length": 20,
        "description": "xai-... bilan boshlanadi",
        "test_endpoint": "https://api.x.ai/v1/models",
        "test_header": lambda key: {"Authorization": f"Bearer {key}"}
    },
    "perplexity": {
        "pattern": r"^pplx-[A-Za-z0-9]+$",
        "prefix": "pplx-",
        "min_length": 30,
        "description": "pplx-... bilan boshlanadi",
        "test_endpoint": "https://api.perplexity.ai/chat/completions",
        "test_header": lambda key: {"Authorization": f"Bearer {key}"}
    },
    "together": {
        "pattern": r"^[A-Za-z0-9]+$",
        "prefix": "",
        "min_length": 20,
        "description": "Harf va raqamlardan iborat",
        "test_endpoint": "https://api.together.xyz/v1/models",
        "test_header": lambda key: {"Authorization": f"Bearer {key}"}
    },
}


def validate_api_key_format(provider: str, api_key: str) -> tuple:
    """
    API kalit formatini tekshiradi.
    
    Returns:
        (is_valid: bool, message: str)
    """
    if not provider or not api_key:
        return False, "❌ Provayder yoki API kaliti bo'sh!"
    
    # Provayder mavjudligini tekshirish
    pattern_info = API_KEY_PATTERNS.get(provider)
    if not pattern_info:
        # Noma'lum provayder uchun umumiy tekshiruv
        if len(api_key) < 15:
            return False, f"❌ API kaliti juda qisqa ({len(api_key)} belgi). Kamida 15 belgi bo'lishi kerak."
        return True, "✅ Format tekshiruvdan o'tdi (umumiy)"
    
    # Uzunlik tekshiruvi
    if len(api_key) < pattern_info["min_length"]:
        return False, f"❌ API kaliti juda qisqa! {pattern_info['min_length']}+ belgi kerak, sizda {len(api_key)} ta."
    
    # Prefix tekshiruvi
    if pattern_info["prefix"] and not api_key.startswith(pattern_info["prefix"]):
        return False, f"❌ Noto'g'ri format! {pattern_info['description']}\n\nKalit '{pattern_info['prefix']}...' bilan boshlanishi kerak.\n\nSizning kalit: {api_key[:10]}..."
    
    # Pattern tekshiruvi
    if not re.match(pattern_info["pattern"], api_key):
        return False, f"❌ API kaliti noto'g'ri formatda!\n\nKutilgan format: {pattern_info['description']}"
    
    return True, "✅ Format tekshiruvdan o'tdi"


async def test_api_key_live(provider: str, api_key: str) -> tuple:
    """
    API kalitni haqiqiy serverda tekshiradi (jonli test).
    
    Returns:
        (is_valid: bool, message: str)
    """
    pattern_info = API_KEY_PATTERNS.get(provider)
    if not pattern_info:
        return True, "⚠️ Jonli tekshiruv o'tkazib bo'lmadi (noma'lum provayder)"
    
    try:
        import aiohttp
        
        url = pattern_info["test_endpoint"]
        headers = pattern_info["test_header"](api_key)
        
        # Gemini uchun maxsus URL
        if provider == "gemini":
            url = f"{url}{api_key}"
            headers = {}
        
        timeout = aiohttp.ClientTimeout(total=15)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            if provider in ["openai", "deepseek", "mistral", "llama", "grok", "together"]:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return True, "✅ API kaliti tasdiqlandi! Serverga ulandi."
                    elif response.status == 401:
                        return False, "❌ API kaliti noto'g'ri! Server ruxsat bermadi (401)."
                    elif response.status == 403:
                        return False, "❌ Ruxsat yo'q! Hisobingizda yetarli mablag' yo'q yoki bloklangan (403)."
                    elif response.status == 429:
                        return True, "⚠️ API kaliti to'g'ri, lekin so'rov limiti oshib ketgan (429)."
                    else:
                        data = await response.json()
                        error_msg = data.get("error", {}).get("message", str(data))
                        return False, f"❌ Server xatosi ({response.status}): {error_msg[:100]}"
            
            elif provider == "claude":
                test_data = {
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
                async with session.post(url, json=test_data, headers=headers) as response:
                    if response.status in [200, 400]:  # 400 = model topildi lekin xabar qisqa
                        return True, "✅ API kaliti tasdiqlandi! Claude serveriga ulandi."
                    elif response.status == 401:
                        return False, "❌ API kaliti noto'g'ri! Claude ruxsat bermadi (401)."
                    else:
                        data = await response.json()
                        error_msg = data.get("error", {}).get("message", str(data))
                        return False, f"❌ Claude xatosi ({response.status}): {error_msg[:100]}"
            
            elif provider == "gemini":
                async with session.get(url) as response:
                    if response.status == 200:
                        return True, "✅ API kaliti tasdiqlandi! Gemini serveriga ulandi."
                    elif response.status == 400:
                        data = await response.json()
                        return False, f"❌ Noto'g'ri kalit: {data.get('error', {}).get('message', 'Xato')[:100]}"
                    else:
                        return False, f"❌ Gemini xatosi ({response.status})"
            
            elif provider == "perplexity":
                test_data = {
                    "model": "llama-3.1-sonar-small-128k-online",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 1
                }
                async with session.post(url, json=test_data, headers=headers) as response:
                    if response.status == 200:
                        return True, "✅ API kaliti tasdiqlandi! Perplexity serveriga ulandi."
                    elif response.status == 401:
                        return False, "❌ API kaliti noto'g'ri! (401)"
                    else:
                        return False, f"❌ Server xatosi ({response.status})"
            
            elif provider == "cohere":
                async with session.get(url, headers=headers) as response:
                    if response.status in [200, 202]:
                        return True, "✅ API kaliti tasdiqlandi! Cohere serveriga ulandi."
                    elif response.status == 401:
                        return False, "❌ API kaliti noto'g'ri! (401)"
                    else:
                        return False, f"❌ Server xatosi ({response.status})"
    
    except aiohttp.ClientError as e:
        return False, f"❌ Ulanish xatoligi: {str(e)[:100]}"
    except Exception as e:
        return False, f"❌ Xatolik: {str(e)[:100]}"


# ========== TIL TANLASH KLAVIATURASI ==========

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Til tanlash klaviaturasi (4 tadan qilib)."""
    buttons = []
    row = []
    for code, name in LANGUAGES.items():
        row.append(InlineKeyboardButton(text=name, callback_data=f"lang_{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ========== ASOSIY MENYU ==========

def get_main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Asosiy menyu klaviaturasi."""
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=get_text(lang, "btn_auto_replies"),
                callback_data="menu_auto_replies"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_text(lang, "btn_status"),
                callback_data="menu_status"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_text(lang, "btn_settings"),
                callback_data="menu_settings"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_text(lang, "btn_language"),
                callback_data="menu_language"
            ),
            InlineKeyboardButton(
                text=get_text(lang, "btn_ai_settings"),
                callback_data="menu_ai_settings"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_text(lang, "btn_help"),
                callback_data="menu_help"
            )
        ],
    ])


def get_back_keyboard(lang: str, callback_data: str = "back_to_main") -> InlineKeyboardMarkup:
    """Orqaga qaytish klaviaturasi."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data=callback_data)]
    ])


# ========== /start ==========

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Botni ishga tushirish."""
    user_id = message.from_user.id
    user = db.get_user(user_id)

    # Foydalanuvchi bazada bo'lmasa, o'zbek tili bilan qo'shish
    if not user:
        db.add_user(user_id, "uz")
        lang = "uz"
    else:
        lang = user.get("language", "uz")

    # Agar foydalanuvchi allaqachon til tanlagan bo'lsa
    if user and user.get("language"):
        await show_main_menu(message, user_id)
        await state.clear()
        return

    # Til tanlashni so'rash
    await message.answer(
        get_text(lang, "start"),
        reply_markup=get_language_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(UserStates.waiting_for_language)


# ========== TIL TANLASH ==========

@router.callback_query(F.data.startswith("lang_"), StateFilter(UserStates.waiting_for_language))
async def select_language(callback: types.CallbackQuery, state: FSMContext):
    """Tilni tanlash."""
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id

    db.update_language(user_id, lang)

    await callback.message.edit_text(
        get_text(lang, "language_selected"),
        parse_mode="HTML"
    )
    await callback.answer()

    # Asosiy menyuni ko'rsatish
    await show_main_menu(callback.message, user_id)
    await state.clear()


@router.callback_query(F.data.startswith("lang_"))
async def change_language(callback: types.CallbackQuery):
    """Tilni o'zgartirish (menyudan)."""
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id

    db.update_language(user_id, lang)

    await callback.message.edit_text(
        get_text(lang, "language_selected"),
        parse_mode="HTML"
    )
    await callback.answer()

    # Asosiy menyuni ko'rsatish
    await show_main_menu(callback.message, user_id)


# ========== ASOSIY MENYUNI KO'RSATISH ==========

async def show_main_menu(message: types.Message, user_id: int):
    """Asosiy menyuni ko'rsatish."""
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    status_map = {
        "active": get_text(lang, "status_active"),
        "paused": get_text(lang, "status_paused"),
        "stopped": get_text(lang, "status_stopped"),
    }
    status = status_map.get(user["bot_status"], get_text(lang, "status_active"))

    replies = db.get_auto_replies(user_id)
    replies_count = len(replies)

    connection = (
        get_text(lang, "connection_yes")
        if user.get("business_connection_id")
        else get_text(lang, "connection_no")
    )

    text = get_text(
        lang, "main_menu",
        status=status,
        replies_count=replies_count,
        connection=connection
    )

    await message.answer(
        text,
        reply_markup=get_main_menu_keyboard(user_id),
        parse_mode="HTML"
    )


# ========== /menu ==========

@router.message(Command("menu"))
async def cmd_menu(message: types.Message):
    """Asosiy menyuni ko'rsatish."""
    await show_main_menu(message, message.from_user.id)


# ========== /help ==========

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Yordam matni."""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    await message.answer(
        get_text(lang, "help_text"),
        reply_markup=get_main_menu_keyboard(user_id),
        parse_mode="HTML"
    )


# ========== MENYU CALLBACKLARI ==========

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    """Asosiy menyuga qaytish."""
    await show_main_menu(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "menu_settings")
async def menu_settings(callback: types.CallbackQuery):
    """Sozlamalar menyusi."""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    await callback.message.edit_text(
        get_text(lang, "settings_menu"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_status"),
                    callback_data="menu_status"
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_language"),
                    callback_data="menu_language"
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_ai_settings"),
                    callback_data="menu_ai_settings"
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text(lang, "btn_back"),
                    callback_data="back_to_main"
                )
            ],
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "menu_language")
async def menu_language(callback: types.CallbackQuery):
    """Til menyusi."""
    await callback.message.edit_text(
        "🌐 Tilni tanlang / Выберите язык / Select language:",
        reply_markup=get_language_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "menu_help")
async def menu_help(callback: types.CallbackQuery):
    """Yordam menyusi."""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    await callback.message.edit_text(
        get_text(lang, "help_text"),
        reply_markup=get_back_keyboard(lang),
        parse_mode="HTML"
    )
    await callback.answer()


# ========== STATUS MENYU ==========

@router.callback_query(F.data == "menu_status")
async def menu_status(callback: types.CallbackQuery):
    """Bot holatini o'zgartirish menyusi."""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    status_map = {
        "active": get_text(lang, "status_active"),
        "paused": get_text(lang, "status_paused"),
        "stopped": get_text(lang, "status_stopped"),
    }
    current_status = status_map.get(user["bot_status"], "Active")

    await callback.message.edit_text(
        get_text(lang, "status_menu", status=current_status),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"🟢 {get_text(lang, 'status_active')}",
                callback_data="set_status_active"
            )],
            [InlineKeyboardButton(
                text=f"🟡 {get_text(lang, 'status_paused')}",
                callback_data="set_status_paused"
            )],
            [InlineKeyboardButton(
                text=f"🔴 {get_text(lang, 'status_stopped')}",
                callback_data="set_status_stopped"
            )],
            [InlineKeyboardButton(
                text=get_text(lang, "btn_back"),
                callback_data="back_to_main"
            )],
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_status_"))
async def set_status(callback: types.CallbackQuery):
    """Bot holatini o'zgartirish."""
    status = callback.data.replace("set_status_", "")
    user_id = callback.from_user.id

    db.update_bot_status(user_id, status)

    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    status_map = {
        "active": get_text(lang, "status_active"),
        "paused": get_text(lang, "status_paused"),
        "stopped": get_text(lang, "status_stopped"),
    }

    await callback.answer(get_text(lang, "status_changed", status=status_map[status]))
    await show_main_menu(callback.message, user_id)


# ========== AVTO-JAVOBLAR MENYU ==========

@router.callback_query(F.data == "menu_auto_replies")
async def menu_auto_replies(callback: types.CallbackQuery):
    """Avto-javoblar menyusi."""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    replies = db.get_auto_replies(user_id)
    count = len(replies)

    await callback.message.edit_text(
        get_text(lang, "auto_replies_menu", count=count),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=get_text(lang, "btn_add_reply"),
                callback_data="add_reply"
            )],
            [InlineKeyboardButton(
                text=get_text(lang, "btn_list_replies"),
                callback_data="list_replies"
            )],
            [InlineKeyboardButton(
                text=get_text(lang, "btn_delete_reply"),
                callback_data="delete_reply"
            )],
            [InlineKeyboardButton(
                text=get_text(lang, "btn_back"),
                callback_data="back_to_main"
            )],
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "add_reply")
async def add_reply_start(callback: types.CallbackQuery, state: FSMContext):
    """Yangi avto-javob qo'shishni boshlash."""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    await callback.message.edit_text(
        get_text(lang, "add_reply_prompt"),
        reply_markup=get_back_keyboard(lang),
        parse_mode="HTML"
    )
    await state.set_state(UserStates.waiting_for_reply)
    await callback.answer()


@router.message(StateFilter(UserStates.waiting_for_reply))
async def process_new_reply(message: types.Message, state: FSMContext):
    """Yangi avto-javobni qabul qilish."""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    text = message.text.strip()
    if "|" not in text:
        await message.answer(
            get_text(lang, "invalid_format"),
            reply_markup=get_back_keyboard(lang),
            parse_mode="HTML"
        )
        return

    parts = text.split("|", 1)
    trigger_text = parts[0].strip()
    reply_text = parts[1].strip()

    if not trigger_text or not reply_text:
        await message.answer(
            get_text(lang, "invalid_format"),
            reply_markup=get_back_keyboard(lang),
            parse_mode="HTML"
        )
        return

    reply_id = db.add_auto_reply(user_id, trigger_text, reply_text)

    await message.answer(
        get_text(lang, "reply_added", id=reply_id),
        parse_mode="HTML"
    )
    await show_main_menu(message, user_id)
    await state.clear()


@router.callback_query(F.data == "list_replies")
async def list_replies(callback: types.CallbackQuery):
    """Avto-javoblar ro'yxatini ko'rsatish."""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    replies = db.get_auto_replies(user_id)

    if not replies:
        await callback.message.edit_text(
            get_text(lang, "no_replies"),
            reply_markup=get_back_keyboard(lang),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text_lines = [f"💬 <b>{get_text(lang, 'btn_auto_replies')}</b>\n"]
    for reply in replies[:20]:  # Maksimum 20 ta ko'rsatish
        text_lines.append(
            f"<b>ID:</b> {reply['id']} | "
            f"<b>Trigger:</b> {reply['trigger_text']} | "
            f"<b>Reply:</b> {reply['reply_text'][:30]}..."
        )

    text = "\n".join(text_lines)

    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard(lang),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "delete_reply")
async def delete_reply_start(callback: types.CallbackQuery, state: FSMContext):
    """Avto-javobni o'chirishni boshlash."""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    await callback.message.edit_text(
        get_text(lang, "delete_reply_prompt"),
        reply_markup=get_back_keyboard(lang),
        parse_mode="HTML"
    )
    await state.set_state(UserStates.waiting_for_delete_id)
    await callback.answer()


@router.message(StateFilter(UserStates.waiting_for_delete_id))
async def process_delete_reply(message: types.Message, state: FSMContext):
    """Avto-javobni o'chirish."""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    try:
        reply_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            get_text(lang, "invalid_format"),
            parse_mode="HTML"
        )
        return

    success = db.delete_auto_reply(user_id, reply_id)

    if success:
        await message.answer(
            get_text(lang, "reply_deleted"),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ Topilmadi yoki o'chirib bo'lmadi.",
            parse_mode="HTML"
        )

    await show_main_menu(message, user_id)
    await state.clear()


# ========== AI SOZLAMALAR MENYU (kelajak uchun) ==========

@router.callback_query(F.data == "menu_ai_settings")
async def menu_ai_settings(callback: types.CallbackQuery):
    """AI sozlamalar menyusi (20 ta provayder bilan)."""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    ai_settings = db.get_ai_settings(user_id)
    current_provider = ai_settings.get("provider", "openai") if ai_settings else "openai"
    status = "✅ Active" if ai_settings and ai_settings.get("is_active") else "❌ Inactive"
    
    provider_name = AIProvider.PROVIDERS.get(current_provider, {}).get("name", "Noma'lum")

    text = (
        f"🤖 <b>AI Sozlamalar</b>\n\n"
        f"📊 Status: {status}\n"
        f"🔌 Provayder: {provider_name}\n"
        f"🔑 API Key: {'✅ Kiritilgan' if ai_settings and ai_settings.get('api_key') else '❌ Kiritilmagan'}\n"
        f"📝 Promt: {'✅ Sozlangan' if ai_settings and ai_settings.get('system_prompt') else '❌ Sozlanmagan'}\n\n"
        f"Amalni tanlang:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔌 Provayder tanlash", callback_data="ai_select_provider")],
            [InlineKeyboardButton(text="🔑 API Key kiritish", callback_data="ai_set_api_key")],
            [InlineKeyboardButton(text="📝 Promt sozlash", callback_data="ai_set_prompt")],
            [InlineKeyboardButton(
                text=f"{'❌ O`chirish' if (ai_settings and ai_settings.get('is_active')) else '✅ Yoqish'}",
                callback_data="ai_toggle"
            )],
            [InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data="menu_settings")],
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "ai_select_provider")
async def ai_select_provider_page(callback: types.CallbackQuery, page: int = 0):
    """Provayder tanlash sahifasi (sahifalangan)."""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    providers = list(AIProvider.PROVIDERS.items())
    per_page = 5
    total_pages = (len(providers) + per_page - 1) // per_page
    start = page * per_page
    end = start + per_page
    page_providers = providers[start:end]

    buttons = []
    for key, info in page_providers:
        buttons.append([InlineKeyboardButton(
            text=f"{info['name']}",
            callback_data=f"ai_provider_{key}"
        )])

    # Navigatsiya tugmalari
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"ai_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"ai_page_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text=get_text(lang, "btn_back"), callback_data="menu_ai_settings")])

    await callback.message.edit_text(
        f"🔌 <b>AI Provayder tanlash</b>\n\nSahifa: {page+1}/{total_pages}\n"
        f"Jami provayder: {len(providers)} ta\n\nProvayderni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ai_page_"))
async def ai_page_navigate(callback: types.CallbackQuery):
    """Provayder sahifalari orasida navigatsiya."""
    page = int(callback.data.split("_")[2])
    await ai_select_provider_page(callback, page)


@router.callback_query(F.data.startswith("ai_provider_"))
async def ai_select_provider_set(callback: types.CallbackQuery):
    """Provayderni tanlash."""
    provider = callback.data.replace("ai_provider_", "")
    user_id = callback.from_user.id
    
    provider_info = AIProvider.PROVIDERS.get(provider)
    if not provider_info:
        await callback.answer("❌ Noma'lum provayder!", show_alert=True)
        return
    
    # Bazaga saqlash
    db.save_ai_provider(user_id, provider)
    
    await callback.answer(f"✅ {provider_info['name']} tanlandi!", show_alert=True)
        await menu_ai_settings(callback)


# ========== AI SOZLAMALAR HANDLERLARI ==========
    
    # ========== AI SOZLAMALAR HANDLERLARI ==========

@router.callback_query(F.data == "ai_set_api_key")
async def ai_set_api_key_menu(callback: types.CallbackQuery):
    """API kalit menyusi."""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"
    
    ai_settings = db.get_ai_settings(user_id)
    has_key = ai_settings and ai_settings.get("api_key")
    provider = ai_settings.get("provider", "openai") if ai_settings else "openai"
    
    try:
        from ai_providers import AIProvider
        provider_name = AIProvider.PROVIDERS.get(provider, {}).get("name", "Noma'lum")
    except:
        provider_name = provider
    
    text = (
        f"🔑 <b>API Kalit Sozlamalari</b>\n\n"
        f"🔌 Joriy provayder: <b>{provider_name}</b>\n"
        f"📌 Status: {'✅ Kiritilgan' if has_key else '❌ Kiritilmagan'}\n"
    )
    
    if has_key:
        masked_key = ai_settings["api_key"][:8] + "..." + ai_settings["api_key"][-4:]
        text += f"🔐 Kalit: <code>{masked_key}</code>\n\n"
    else:
        text += "\n"
    
    buttons = [
        [InlineKeyboardButton(
            text="➕ Yangi kalit kiritish" if not has_key else "🔄 Kalitni almashtirish",
            callback_data="ai_enter_api_key"
        )]
    ]
    
    if has_key:
        buttons.append([
            InlineKeyboardButton(text="🗑 Kalitni o'chirish", callback_data="ai_delete_api_key"),
            InlineKeyboardButton(text="🔍 Kalitni tekshirish", callback_data="ai_test_api_key")
        ])
    
    buttons.append([InlineKeyboardButton(
        text=get_text(lang, "btn_back"), callback_data="menu_ai_settings"
    )])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "ai_enter_api_key")
async def ai_enter_api_key_start(callback: types.CallbackQuery, state: FSMContext):
    """API kalit kiritishni boshlash."""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"
    
    ai_settings = db.get_ai_settings(user_id)
    provider = ai_settings.get("provider", "openai") if ai_settings else "openai"
    
    try:
        from ai_providers import AIProvider
        provider_name = AIProvider.PROVIDERS.get(provider, {}).get("name", "Noma'lum")
    except:
        provider_name = provider
    
    pattern_info = API_KEY_PATTERNS.get(provider, {})
    format_desc = pattern_info.get("description", "Maxsus formatda")
    
    await callback.message.edit_text(
        f"🔑 <b>API Kalit Kiritish</b>\n\n"
        f"🔌 Provayder: <b>{provider_name}</b>\n"
        f"📋 Format: {format_desc}\n\n"
        f"⚠️ <b>Xavfsizlik:</b>\n"
        f"• Kalitingiz shifrlangan bazada saqlanadi\n"
        f"• Hech kim ko'ra olmaydi\n"
        f"• Istalgan vaqt o'chirishingiz mumkin\n\n"
        f"📝 API kalitingizni yuboring:",
        reply_markup=get_back_keyboard(lang, "ai_set_api_key"),
        parse_mode="HTML"
    )
    await state.set_state(UserStates.waiting_for_ai_api_key)
    await callback.answer()


@router.message(StateFilter(UserStates.waiting_for_ai_api_key))
async def process_api_key(message: types.Message, state: FSMContext):
    """API kalitini tekshirish va saqlash."""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"
    
    api_key = message.text.strip()
    
    # Xavfsizlik: kalitni logga yozmaslik, xabarni o'chirish
    try:
        await message.delete()
    except:
        pass
    
    ai_settings = db.get_ai_settings(user_id)
    provider = ai_settings.get("provider", "openai") if ai_settings else "openai"
    
    try:
        from ai_providers import AIProvider
        provider_name = AIProvider.PROVIDERS.get(provider, {}).get("name", "Noma'lum")
    except:
        provider_name = provider
    
    # 1-bosqich: Format tekshiruvi
    status_msg = await message.answer("🔍 API kaliti tekshirilmoqda...", parse_mode="HTML")
    
    is_valid_format, format_msg = validate_api_key_format(provider, api_key)
    
    if not is_valid_format:
        await status_msg.edit_text(
            f"{format_msg}\n\n⚠️ Iltimos, {provider_name} uchun to'g'ri API kalitini kiriting.",
            reply_markup=get_back_keyboard(lang, "ai_set_api_key"),
            parse_mode="HTML"
        )
        await state.set_state(UserStates.waiting_for_ai_api_key)
        return
    
    # 2-bosqich: Jonli tekshiruv
    await status_msg.edit_text(
        f"✅ Format to'g'ri\n🔄 {provider_name} serveriga ulanmoqda...",
        parse_mode="HTML"
    )
    
    is_valid_live, live_msg = await test_api_key_live(provider, api_key)
    
    if not is_valid_live:
        await status_msg.edit_text(
            f"❌ <b>Tekshiruv muvaffaqiyatsiz!</b>\n\n"
            f"{live_msg}\n\n"
            f"⚠️ Kalit saqlanmadi. Qaytadan urinib ko'ring.",
            reply_markup=get_back_keyboard(lang, "ai_set_api_key"),
            parse_mode="HTML"
        )
        await state.set_state(UserStates.waiting_for_ai_api_key)
        return
    
    # 3-bosqich: Saqlash
    db.save_ai_settings(user_id, api_key=api_key)
    
    masked_key = api_key[:8] + "..." + api_key[-4:]
    
    await status_msg.edit_text(
        f"✅ <b>API kaliti muvaffaqiyatli saqlandi!</b>\n\n"
        f"🔌 Provayder: {provider_name}\n"
        f"🔐 Kalit: <code>{masked_key}</code>\n"
        f"📊 Status: {live_msg}\n\n"
        f"Endi AI rejimini yoqishingiz mumkin.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 AI ni yoqish", callback_data="ai_toggle")],
            [InlineKeyboardButton(text="⬅️ AI sozlamalarga qaytish", callback_data="menu_ai_settings")],
        ]),
        parse_mode="HTML"
    )
    await state.clear()


@router.callback_query(F.data == "ai_delete_api_key")
async def ai_delete_api_key(callback: types.CallbackQuery):
    """API kalitini o'chirish."""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"
    
    db.save_ai_settings(user_id, api_key="", is_active=0)
    
    await callback.message.edit_text(
        "🗑 <b>API kaliti o'chirildi!</b>\n\n"
        "AI rejimi avtomatik o'chirildi.\n"
        "Yangi kalit kiritish uchun quyidagi tugmani bosing.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yangi kalit kiritish", callback_data="ai_enter_api_key")],
            [InlineKeyboardButton(text="⬅️ AI sozlamalarga qaytish", callback_data="menu_ai_settings")],
        ]),
        parse_mode="HTML"
    )
    await callback.answer("✅ API kaliti o'chirildi!", show_alert=True)


@router.callback_query(F.data == "ai_test_api_key")
async def ai_test_api_key(callback: types.CallbackQuery):
    """Mavjud API kalitini tekshirish."""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"
    
    ai_settings = db.get_ai_settings(user_id)
    
    if not ai_settings or not ai_settings.get("api_key"):
        await callback.answer("❌ Avval API kalitini kiriting!", show_alert=True)
        return
    
    await callback.answer("🔄 Tekshirilmoqda...", show_alert=False)
    
    api_key = ai_settings["api_key"]
    provider = ai_settings.get("provider", "openai")
    
    try:
        from ai_providers import AIProvider
        provider_name = AIProvider.PROVIDERS.get(provider, {}).get("name", "Noma'lum")
    except:
        provider_name = provider
    
    is_valid_live, live_msg = await test_api_key_live(provider, api_key)
    
    if is_valid_live:
        await callback.answer(f"✅ {provider_name}: {live_msg}", show_alert=True)
    else:
        await callback.answer(f"❌ {provider_name}: {live_msg}", show_alert=True)


@router.callback_query(F.data == "ai_set_prompt")
async def ai_set_prompt_start(callback: types.CallbackQuery, state: FSMContext):
    """AI tizim promtini kiritishni boshlash."""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    current_settings = db.get_ai_settings(user_id)
    current_prompt = current_settings.get("system_prompt", "") if current_settings else ""

    await callback.message.edit_text(
        "📝 <b>Tizim promtini kiriting:</b>\n\n"
        "Bu AI ga qanday javob berishi kerakligini ko'rsatadi.\n\n"
        f"Joriy promt: <code>{current_prompt or 'O`rnatilmagan'}</code>\n\n"
        "Yangi promt matnini yuboring:",
        reply_markup=get_back_keyboard(lang, "menu_ai_settings"),
        parse_mode="HTML"
    )
    await state.set_state(UserStates.waiting_for_ai_prompt)
    await callback.answer()


@router.message(StateFilter(UserStates.waiting_for_ai_prompt))
async def process_ai_prompt(message: types.Message, state: FSMContext):
    """AI tizim promtini saqlash."""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    system_prompt = message.text.strip()

    if not system_prompt:
        await message.answer(
            "❌ Promt bo'sh bo'lishi mumkin emas! Qaytadan yuboring.",
            reply_markup=get_back_keyboard(lang, "menu_ai_settings"),
            parse_mode="HTML"
        )
        return

    # Promtni saqlash
    db.save_ai_settings(user_id, system_prompt=system_prompt)

    await message.answer(
        f"✅ Tizim promti muvaffaqiyatli saqlandi!\n\n"
        f"<code>{system_prompt[:100]}{'...' if len(system_prompt) > 100 else ''}</code>",
        parse_mode="HTML"
    )
    await show_main_menu(message, user_id)
    await state.clear()


@router.callback_query(F.data == "ai_toggle")
async def ai_toggle(callback: types.CallbackQuery):
    """AI rejimini yoqish/o'chirish."""
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    ai_settings = db.get_ai_settings(user_id)

    if not ai_settings or not ai_settings.get("api_key"):
        await callback.answer("❌ Avval API kalitini kiriting!", show_alert=True)
        return

    new_status = 0 if ai_settings.get("is_active") else 1
    db.save_ai_settings(user_id, is_active=new_status)

    status_text = "✅ Yoqildi" if new_status else "❌ O'chirildi"
    await callback.answer(f"AI rejimi {status_text}", show_alert=True)

    # Menyuni yangilash
    await menu_ai_settings(callback)


# ========== NOMA'LUM XABARLAR ==========

@router.message()
async def unknown_message(message: types.Message):
    """Noma'lum xabarlarga javob."""
    user_id = message.from_user.id
    user = db.get_user(user_id)
    lang = user["language"] if user else "en"

    await message.answer(
        get_text(lang, "unknown_command"),
        parse_mode="HTML"
    )