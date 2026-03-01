import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from yt_dlp import YoutubeDL

# Logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("TG_TOKEN")
user_settings = {}

def download_video_sync(url, user_id):
    # Fixed Path for GitHub Actions
    cookie_path = 'cookies.txt'
    
    # 4K/1080p selection logic [cite: 4, 5]
    quality = user_settings.get(user_id, {}).get("quality", "best")
    format_str = "bestvideo+bestaudio/best" if quality == "best" else f"bestvideo[height<={quality}]+bestaudio/best"

    ydl_opts = {
        'format': format_str,
        'merge_output_format': 'mp4',
        'cookiefile': cookie_path,
        'quiet': False,
        'no_warnings': False,
        # Mandatory Bypass Options 
        'geo_bypass': True,
        'geo_bypass_country': 'IN',
        'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web']}},
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'outtmpl': f'downloads/{user_id}_%(id)s.%(ext)s',
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # Extension fix for merged files
        if not filename.endswith('.mp4'):
            filename = filename.rsplit('.', 1)[0] + '.mp4'
        return filename

async def process_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "youtu" not in url: return
    
    status = await update.message.reply_text("🚀 **Bypassing Region Locks...**\n(Using Indian Session)", parse_mode="Markdown")
    
    try:
        if not os.path.exists('cookies.txt'):
            raise Exception("Cookie file missing on server!")

        file_path = await asyncio.to_thread(download_video_sync, url, update.effective_user.id)
        
        await status.edit_text("⬆️ **Uploading 4K Document...**", parse_mode="Markdown")
        
        # Document policy 
        with open(file_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                caption=f"✅ Video Ready for Editing!",
                write_timeout=300
            )
        os.remove(file_path)
        await status.delete()
        
    except Exception as e:
        await status.edit_text(f"❌ **Bypass Failed:**\n`{str(e)}`", parse_mode="Markdown")

# ... (Start/Settings handlers are same as before) [cite: 3]    await asyncio.sleep(minutes * 60)
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
