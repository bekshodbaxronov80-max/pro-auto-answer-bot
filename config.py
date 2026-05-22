import os

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

if not BOT_TOKEN:
    BOT_TOKEN = "8956169061:AAGk93ybwSEsEoyb8tbVdi8gX7xWbunKap8"