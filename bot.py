import logging
from datetime import datetime

import pytz
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

import database as db
import ai_analyzer
from config import BOT_TOKEN, CHAT_ID, TIMEZONE, WAKE_UP_HOUR, WAKE_UP_MINUTE, SLEEP_REMINDER_HOUR, SLEEP_REMINDER_MINUTE, TIMEOUT_MINUTES

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARNING,
)
logger = logging.getLogger(__name__)

tz = pytz.timezone(TIMEZONE)


# ──────────────────────────────────────────────
# /start
# ──────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ai_status = "🟢 Aktif" if ai_analyzer.ai_enabled() else "⚪ Nonaktif"
    await update.message.reply_text(
        "Halo! Aku bot wake-up checker kamu.\n\n"
        f"⏰ Setiap jam {WAKE_UP_HOUR:02d}:{WAKE_UP_MINUTE:02d} aku akan tanya kamu bangun atau engga.\n"
        f"Kalo ga respon dalam {TIMEOUT_MINUTES} menit, otomatis TIDAK BANGUN.\n\n"
        f"🌙 Setiap jam {SLEEP_REMINDER_HOUR:02d}:{SLEEP_REMINDER_MINUTE:02d} aku akan remind kamu buat tidur.\n\n"
        f"🤖 AI Coach: {ai_status}\n\n"
        "Perintah:\n"
        "/stats - Lihat statistik + analisis AI\n"
        "/history - Lihat history 7 hari terakhir\n"
        "/test_send - Test kirim pesan bangun sekarang\n"
        "/test_sleep - Test kirim reminder tidur sekarang\n"
        f"/set_timeout [menit] - Ganti timeout (sekarang: {TIMEOUT_MINUTES}m)"
    )


# ──────────────────────────────────────────────
# /stats
# ──────────────────────────────────────────────
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = db.get_stats()
    history = db.get_history(14)

    if stats["total"] == 0:
        await update.message.reply_text("Belum ada data. Coba /test_send dulu buat test!")
        return

    win_rate = (stats["wins"] / stats["total"] * 100) if stats["total"] > 0 else 0

    text = (
        "📊 Statistik Wake-Up\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 Kemenangan: {stats['wins']}\n"
        f"💀 Kekalahan:  {stats['losses']}\n"
        f"📅 Total hari:  {stats['total']}\n"
        f"🔥 Streak:      {stats['streak']} hari\n"
        f"📈 Win rate:    {win_rate:.1f}%\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
    )

    if stats["streak"] >= 7:
        text += "🔥🔥🔥 STREAK GILA BRO! 🔥🔥🔥"
    elif stats["streak"] >= 3:
        text += "💪 Lagi on fire nih!"
    elif stats["wins"] > stats["losses"]:
        text += "👍 Bagus, keep going!"
    else:
        text += "😤 Semangat ya!"

    await update.message.reply_text(text, parse_mode="HTML")

    # AI analysis (kalau enabled)
    if ai_analyzer.ai_enabled():
        await update.message.reply_text("🤖 AI lagi analisis data kamu...")
        result = ai_analyzer.ask_ai(stats, history)
        if result:
            await update.message.reply_text(
                f"🤖 <b>AI Coach</b>:\n\n{result}",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text("⚠️ AI lagi error, coba lagi nanti.")


# ──────────────────────────────────────────────
# /history
# ──────────────────────────────────────────────
async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = db.get_history(7)
    if not rows:
        await update.message.reply_text("Belum ada history.")
        return

    text =     text = "📋 History 7 Hari Terakhir\n━━━━━━━━━━━━━━━━━━━━\n"
    for row in rows:
        icon = "✅" if row["status"] == "bangun" else "❌"
        text += f"{icon} {row['date']} - {row['time'] or '?'}\n"

    await update.message.reply_text(text)


# ──────────────────────────────────────────────
# /test_send (test kirim pesan)
# ──────────────────────────────────────────────
async def cmd_test_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_wake_up_message(context, update.effective_chat.id)

    # Schedule timeout check juga
    context.job_queue.run_once(
        check_no_response,
        TIMEOUT_MINUTES * 60,
        data=update.effective_chat.id,
    )

    await update.message.reply_text(
        f"Pesan test dikirim! Kalo ga respon {TIMEOUT_MINUTES} menit, otomatis TIDAK BANGUN."
    )


# ──────────────────────────────────────────────
# /test_sleep (test sleep reminder)
# ──────────────────────────────────────────────
async def cmd_test_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_sleep_reminder(context, update.effective_chat.id)
    await update.message.reply_text("Pesan sleep reminder test dikirim!")


# ──────────────────────────────────────────────
# /set_timeout
# ──────────────────────────────────────────────
async def cmd_set_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import config

    if not context.args:
        await update.message.reply_text(
            f"Timeout sekarang: {config.TIMEOUT_MINUTES} menit\n"
            f"Cara pakai: /set_timeout 90"
        )
        return

    try:
        minutes = int(context.args[0])
        if minutes < 5 or minutes > 360:
            await update.message.reply_text("Timeout harus antara 5-360 menit.")
            return
        config.TIMEOUT_MINUTES = minutes
        await update.message.reply_text(f"✅ Timeout diubah ke {minutes} menit.")
    except ValueError:
        await update.message.reply_text("Harus angka! Contoh: /set_timeout 90")


# ──────────────────────────────────────────────
# Kirim pesan wake-up dengan tombol
# ──────────────────────────────────────────────
async def send_wake_up_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    keyboard = [
        [
            InlineKeyboardButton("Bangun ✅", callback_data="bangun"),
            InlineKeyboardButton("Tidak ❌", callback_data="tidak_bangun"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=chat_id,
        text="⏰ Pagi! Udah bangun belum?\n\nKlik tombol di bawah:",
        reply_markup=reply_markup,
    )


# ──────────────────────────────────────────────
# Kirim pesan sleep reminder jam 8 malam
# ──────────────────────────────────────────────
async def send_sleep_reminder(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    keyboard = [
        [
            InlineKeyboardButton("Sudah tidur 😴", callback_data="sudah_tidur"),
            InlineKeyboardButton("Belum 😅", callback_data="belum_tidur"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=chat_id,
        text="🌙 Sudah jam 8 malam nih!\n\nWaktunya mulai ngeredupin layar & persiapin tidur ya.\nKlik tombol di bawah:",
        reply_markup=reply_markup,
    )


# ──────────────────────────────────────────────
# Handle tombol callback
# ──────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    now = datetime.now(tz)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    status = query.data  # "bangun" atau "tidak_bangun"

    # Cek udah jawab belum hari ini
    existing = db.get_today_status(date_str)
    if existing:
        status_text = "Bangun ✅" if existing == "bangun" else "Tidak Bangun ❌"
        await query.edit_message_text(
            f"Kamu udah jawab hari ini: {status_text}\n"
            f"Waktu jawab: {time_str}"
        )
        return

    db.save_response(date_str, status, time_str)

    if status == "bangun":
        stats = db.get_stats()
        await query.edit_message_text(
            f"✅ Bangun on time!\n"
            f"Waktu: {time_str}\n\n"
            f"🏆 Total kemenangan: {stats['wins']}\n"
            f"🔥 Streak: {stats['streak']} hari"
        )
    else:
        await query.edit_message_text(
            f"❌ Yaudah tidur lagi ya...\n"
            f"Waktu jawab: {time_str}\n\n"
            f"Besok semangat lagi!"
        )


# ──────────────────────────────────────────────
# Handle tombol sleep reminder
# ──────────────────────────────────────────────
async def sleep_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data  # "sudah_tidur" atau "belum_tidur"

    if data == "sudah_tidur":
        await query.edit_message_text(
            "😴 Mantap! Tidur cukup biar besok fresh bangun subuh.\n\nSelamat malam & sweet dreams! 🌙"
        )
    else:
        await query.edit_message_text(
            "😅 Yaudah, tapi coba mulai ngeredupin layar HP ya.\nMata butuh istirahat biar besok ga ngantuk banget.\n\nSemoga cepet tidur! 🌙"
        )


# ──────────────────────────────────────────────
# Scheduler job
# ──────────────────────────────────────────────
async def scheduled_wake_up(context: ContextTypes.DEFAULT_TYPE):
    await send_wake_up_message(context, CHAT_ID)

    # Schedule timeout check
    context.job_queue.run_once(
        check_no_response,
        TIMEOUT_MINUTES * 60,  # convert to seconds
        data=CHAT_ID,
    )

    logger.debug(f"Wake-up message sent! Timeout check in {TIMEOUT_MINUTES} minutes.")


# ──────────────────────────────────────────────
# Sleep reminder scheduler job
# ──────────────────────────────────────────────
async def scheduled_sleep_reminder(context: ContextTypes.DEFAULT_TYPE):
    await send_sleep_reminder(context, CHAT_ID)
    logger.debug("Sleep reminder sent!")


# ──────────────────────────────────────────────
# Cek kalo user ga respon → auto "tidak_bangun"
# ──────────────────────────────────────────────
async def check_no_response(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(tz)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    existing = db.get_today_status(date_str)
    if existing:
        # Udah jawab, skip
        return

    # Belum jawab → auto "tidak_bangun"
    db.save_response(date_str, "tidak_bangun", time_str)

    await context.bot.send_message(
        chat_id=context.job.data,
        text=f"😴 Kamu ga respon dalam {TIMEOUT_MINUTES} menit.\n"
             f"Otomatis dicatat sebagai TIDAK BANGUN.\n\n"
             f"Besok semangat lagi ya!",
    )
    logger.debug(f"No response for {date_str}, auto-marked as tidak_bangun")


# ──────────────────────────────────────────────
# Global error handler: log error sekali aja
# ──────────────────────────────────────────────
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")
    try:
        if update and update.effective_chat:
            await context.bot.send_message(
                update.effective_chat.id,
                "⚠️ Ada error kecil, coba lagi ya.",
            )
    except Exception:
        pass


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ERROR: Set BOT_TOKEN di config.py atau environment variable!")
        print("Cara: export BOT_TOKEN='token_dari_botfather'")
        return

    if CHAT_ID == 0:
        print("ERROR: Set CHAT_ID di config.py atau environment variable!")
        print("Cara: export CHAT_ID='chat_id_kamu'")
        print("Dapet dari @userinfobot di Telegram")
        return

    db.init_db()

    # Set bot commands menu di Telegram
    async def post_init(application: Application):
        await application.bot.set_my_commands([
            BotCommand("start", "Mulai bot"),
            BotCommand("stats", "Lihat statistik"),
            BotCommand("history", "History 7 hari terakhir"),
            BotCommand("test_send", "Test kirim pesan bangun"),
            BotCommand("test_sleep", "Test reminder tidur"),
            BotCommand("set_timeout", "Ganti timeout (menit)"),
        ])

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Error handler: log sekali, ga spam traceback
    app.add_error_handler(error_handler)

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("test_send", cmd_test_send))
    app.add_handler(CommandHandler("test_sleep", cmd_test_sleep))
    app.add_handler(CommandHandler("set_timeout", cmd_set_timeout))

    # Callback handler untuk tombol
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(bangun|tidak_bangun)$"))
    app.add_handler(CallbackQueryHandler(sleep_button_handler, pattern="^(sudah_tidur|belum_tidur)$"))

    # Scheduler
    from datetime import time as dt_time

    job_queue = app.job_queue
    job_queue.run_daily(
        scheduled_wake_up,
        time=dt_time(hour=WAKE_UP_HOUR, minute=WAKE_UP_MINUTE, second=0, tzinfo=tz),
    )

    # Sleep reminder jam 8 malam
    job_queue.run_daily(
        scheduled_sleep_reminder,
        time=dt_time(hour=SLEEP_REMINDER_HOUR, minute=SLEEP_REMINDER_MINUTE, second=0, tzinfo=tz),
    )

    print(f"Bot jalan! Jam {WAKE_UP_HOUR:02d}:{WAKE_UP_MINUTE:02d} pesan bangun, jam {SLEEP_REMINDER_HOUR:02d}:{SLEEP_REMINDER_MINUTE:02d} reminder tidur.")
    app.run_polling()


if __name__ == "__main__":
    main()
