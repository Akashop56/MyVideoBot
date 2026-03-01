import os
import asyncio
import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from yt_dlp import YoutubeDL

# Logging Setup
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TG_TOKEN")
# Settings Storage: {user_id: {"quality": "1080", "mode": "fixed", "cleanup": 5}}
user_settings = {}

# Progress Hook for yt-dlp
def progress_hook(d, context, chat_id, message_id):
    if d['status'] == 'downloading':
        p = d.get('_percent_str', '0%')
        s = d.get('_speed_str', '0B/s')
        e = d.get('_eta_str', '00:00')
        text = f"⬇️ **Downloading...**\n━━━━━━━━━━━━\n📊 Progress: {p}\n🚀 Speed: {s}\n⏳ ETA: {e}"
        # Running edit in async loop
        asyncio.run_coroutine_threadsafe(
            context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="Markdown"),
            context.application.loop
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_settings:
        user_settings[user_id] = {"quality": "best", "mode": "fixed", "cleanup": 5}
    await update.message.reply_text("👋 Welcome Akash! Send a YouTube link to start.\nUse /settings to configure quality.")

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎬 Default Quality", callback_data="set_q")],
        [InlineKeyboardButton("🔁 Download Mode", callback_data="set_m")],
        [InlineKeyboardButton("🧹 Cleanup Timer", callback_data="set_c")],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ]
    await update.message.reply_text("⚙️ **Bot Settings**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "set_q":
        keys = [[InlineKeyboardButton(q, callback_data=f"q_{q}")] for q in ["360", "480", "720", "1080", "best"]]
        await query.edit_message_text("Select Video Quality:", reply_markup=InlineKeyboardMarkup(keys))
    elif query.data.startswith("q_"):
        val = query.data.split("_")[1]
        user_settings[user_id]["quality"] = val
        await query.edit_message_text(f"✅ Default quality set to {val}p.")
    elif query.data == "close":
        await query.message.delete()

async def handle_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.effective_user.id
    if "youtube.com" not in url and "youtu.be" not in url:
        return

    status_msg = await update.message.reply_text("🔎 Analyzing video...")
    
    # User Preferences
    pref = user_settings.get(user_id, {"quality": "best", "cleanup": 5})
    quality = pref["quality"]
    format_str = "bestvideo+bestaudio/best" if quality == "best" else f"bestvideo[height<={quality}]+bestaudio/best"

    ydl_opts = {
        'format': format_str,
        'merge_output_format': 'mp4',
        'cookiefile': 'cookies.txt',
        'outtmpl': f'downloads/{user_id}_%(id)s.%(ext)s',
        'progress_hooks': [lambda d: progress_hook(d, context, update.effective_chat.id, status_msg.message_id)],
        'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
    }

    try:
        if not os.path.exists('downloads'): os.makedirs('downloads')
        
        with YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            file_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp4'

        await status_msg.edit_text("⬆️ Uploading Document (No Compression)...")
        
        with open(file_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                caption=f"✅ {info['title']}\n🌟 Quality: {quality}p",
                write_timeout=300
            )

        # Cleanup Logic 
        await status_msg.delete()
        asyncio.create_task(auto_delete(file_path, pref['cleanup']))

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

async def auto_delete(path, minutes):
    await asyncio.sleep(minutes * 60)
    if os.path.exists(path):
        os.remove(path)
        logger.info(f"Cleaned up: {path}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settings", settings_menu))
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_download))
    app.run_polling()

if __name__ == "__main__":
    main()
