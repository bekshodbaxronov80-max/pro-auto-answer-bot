import os
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
if not BOT_TOKEN:
    try:
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("TELEGRAM_TOKEN="):
                    BOT_TOKEN = line.split("=", 1)[1].strip()
    except: pass