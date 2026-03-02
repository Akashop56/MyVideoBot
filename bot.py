import os
import asyncio
import logging
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from yt_dlp import YoutubeDL

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TG_TOKEN")
user_links = {}

# ---------- Animated Progress Bar ----------
def progress_bar(percent):
    p = float(percent.replace('%','').strip())
    filled = int(p // 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"[{bar}] {percent}"

def progress_hook(d, context, chat_id, message_id):
    if d["status"] == "downloading":
        percent = d.get("_percent_str", "0%")
        speed = d.get("_speed_str", "0B/s")
        eta = d.get("_eta_str", "00:00")

        text = (
            f"⬇️ Downloading...\n"
            f"{progress_bar(percent)}\n"
            f"🚀 {speed} | ⏳ {eta}"
        )

        try:
            asyncio.run_coroutine_threadsafe(
                context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                ),
                context.application.loop,
            )
        except:
            pass


# ---------- Start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send YouTube link.")


# ---------- Handle Link ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if "youtu" not in url:
        return

    user_links[update.effective_user.id] = url
    await update.message.reply_text("🔍 Fetching available qualities...")

    ydl_opts = {
        "quiet": True,
        "cookiefile": "cookies.txt",
        "geo_bypass": True,
        "noplaylist": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=False)

        formats = info.get("formats", [])
        heights = sorted(
            list(
                set(
                    f.get("height")
                    for f in formats
                    if f.get("height") and f.get("ext") == "mp4"
                )
            ),
            reverse=True,
        )

        if not heights:
            await update.message.reply_text("❌ No MP4 qualities found.")
            return

        keyboard = []
        row = []
        for h in heights[:6]:  # max 6 buttons
            row.append(
                InlineKeyboardButton(f"{h}p", callback_data=str(h))
            )
            if len(row) == 2:
                keyboard.append(row)
                row = []

        if row:
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("⚡ Best", callback_data="best")])

        await update.message.reply_text(
            "🎥 Select Quality:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error:\n{str(e)}")


# ---------- Download ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    quality = query.data
    user_id = query.from_user.id

    if user_id not in user_links:
        await query.edit_message_text("Session expired. Send link again.")
        return

    url = user_links[user_id]
    status = await query.edit_message_text("🚀 Starting download...")

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    if quality == "best":
        format_string = "(bv*+ba/b)[ext=mp4]/best"
    else:
        format_string = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best"

    ydl_opts = {
        "format": format_string,
        "merge_output_format": "mp4",
        "cookiefile": "cookies.txt",
        "geo_bypass": True,
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 5,
        "noplaylist": True,
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "progress_hooks": [
            lambda d: progress_hook(
                d,
                context,
                query.message.chat_id,
                status.message_id,
            )
        ],
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(
                ydl.extract_info, url, download=True
            )
            file_path = ydl.prepare_filename(info).rsplit(".", 1)[0] + ".mp4"

        await status.edit_text("⬆️ Uploading...")

        file_size = os.path.getsize(file_path)

        # -------- Auto send as video if small ----------
        if file_size < 50 * 1024 * 1024:  # 50MB
            with open(file_path, "rb") as f:
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=f,
                    caption=f"🎬 {info.get('title','Video')}",
                    supports_streaming=True,
                )
        else:
            with open(file_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    caption=f"📁 {info.get('title','Video')}",
                )

        os.remove(file_path)
        await status.delete()

    except Exception as e:
        await status.edit_text(f"❌ Error:\n{str(e)}")


# ---------- Crash Safe Restart ----------
async def error_handler(update, context):
    logging.error(msg="Exception while handling update:", exc_info=context.error)

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)

    print("Bot Started...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"Bot crashed: {e}")
            print("Restarting in 5 seconds...")
            asyncio.sleep(5)
