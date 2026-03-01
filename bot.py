import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from yt_dlp import YoutubeDL

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Token from Environment Variable
TOKEN = os.getenv("TG_TOKEN")

# Simple memory storage for User Settings (Per-user)
user_settings = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_settings:
        user_settings[user_id] = {"quality": "best", "mode": "fixed", "cleanup": 5}
    await update.message.reply_text("👋 Hello Akash! Send me a YouTube link to download.\nUse /settings to change quality.")

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Settings menu using Inline Keyboard"""
    keyboard = [
        [InlineKeyboardButton("🎬 Default Video Quality", callback_data="set_quality")],
        [InlineKeyboardButton("🔁 Download Mode", callback_data="set_mode")],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⚙️ **Settings Menu**", reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "set_quality":
        keyboard = [
            [InlineKeyboardButton("360p", callback_data="q_360"), InlineKeyboardButton("720p", callback_data="q_720")],
            [InlineKeyboardButton("1080p", callback_data="q_1080"), InlineKeyboardButton("4K/Best", callback_data="q_best")]
        ]
        await query.edit_message_text(text="Select Default Quality:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data.startswith("q_"):
        quality = query.data.split("_")[1]
        user_settings[update.effective_user.id]["quality"] = quality
        await query.edit_message_text(text=f"✅ Default quality set to: {quality}")
        
    elif query.data == "close":
        await query.message.delete()

def download_video_sync(url, user_id, message_id):
    """yt-dlp python API (Runs in thread to avoid blocking)"""
    quality_pref = user_settings.get(user_id, {}).get("quality", "best")
    format_string = "bestvideo+bestaudio/best" if quality_pref == "best" else f"bestvideo[height<={quality_pref}]+bestaudio/best"
    
    ydl_opts = {
        'format': format_string,
        'merge_output_format': 'mp4',
        'outtmpl': f'download_{user_id}_%(id)s.%(ext)s',
        'cookiefile': 'cookies.txt', # Using your cookies
        'quiet': True,
        'no_warnings': True
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # Ensure correct extension after merge
        if not filename.endswith('.mp4'):
            filename = filename.rsplit('.', 1)[0] + '.mp4'
        return filename

async def process_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.effective_user.id
    
    if "youtu" not in url:
        return
        
    msg = await update.message.reply_text("⏳ Processing link & checking cookies...")
    
    try:
        # Run yt-dlp in a separate thread so bot doesn't freeze
        filename = await asyncio.to_thread(download_video_sync, url, user_id, msg.message_id)
        
        await msg.edit_text("⬆️ Downloading complete. Uploading to Telegram as Document...")
        
        # Uploading strictly as document as per your rules
        with open(filename, 'rb') as doc:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=doc,
                caption="✅ Downloaded using yt-dlp Python API",
                reply_to_message_id=update.message.message_id,
                write_timeout=60,
                read_timeout=60
            )
            
        # Auto Cleanup
        os.remove(filename)
        await msg.delete()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await msg.edit_text(f"❌ **Error:**\n`{str(e)}`\nMake sure your cookies.txt is valid.", parse_mode="Markdown")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settings", settings)) # Settings feature added
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_link))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
