import os
from dotenv import load_dotenv

# Load semua config dari file .env (satu folder yang sama)
load_dotenv()

# Telegram Bot Token dari @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Chat ID kamu (bisa dapet dari @userinfobot di Telegram)
CHAT_ID = int(os.getenv("CHAT_ID", "0"))

# Jam kirim pesan (24 format)
WAKE_UP_HOUR = int(os.getenv("WAKE_UP_HOUR", "4"))
WAKE_UP_MINUTE = int(os.getenv("WAKE_UP_MINUTE", "0"))

# Sleep reminder (jam 8 malam)
SLEEP_REMINDER_HOUR = int(os.getenv("SLEEP_REMINDER_HOUR", "20"))
SLEEP_REMINDER_MINUTE = int(os.getenv("SLEEP_REMINDER_MINUTE", "0"))

# Timeout: berapa menit kalo ga respon, otomatis "tidak bangun"
TIMEOUT_MINUTES = int(os.getenv("TIMEOUT_MINUTES", "5"))

# Timezone
TIMEZONE = os.getenv("TIMEZONE", "Asia/Jakarta")

# ──────────────────────────────────────────────
# OpenRouter AI (opsional, gratis pake model kayak below)
# Buat analisis statistik + motivasi saat /stats
# ──────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
# Model gratis bisa cek di https://openrouter.ai/models
AI_MODEL = os.getenv("AI_MODEL", "inclusionai/ling-3.0-flash-fin:free")
# Set ke False kalo ga mau pake AI
AI_ENABLED = os.getenv("AI_ENABLED", "true").strip().lower() in ("1", "true", "yes")
