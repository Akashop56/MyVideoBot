import os, asyncio, logging, base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from yt_dlp import YoutubeDL

# Logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("TG_TOKEN")
user_settings = {} # {user_id: {"q": "best"}}

# Progress Hook for Live Updates
def progress_hook(d, context, chat_id, message_id):
    if d['status'] == 'downloading':
        p = d.get('_percent_str', '0%')
        s = d.get('_speed_str', '0B/s')
        e = d.get('_eta_str', '00:00')
        text = f"⬇️ **Downloading...**\n━━━━━━━━━━━━\n📊 Progress: {p}\n🚀 Speed: {s}\n⏳ ETA: {e}"
        try:
            asyncio.run_coroutine_threadsafe(
                context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="Markdown"),
                context.application.loop
            )
        except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello Akash! YouTube link bhejo. 4K aur India-only videos (IPL) ab bypass ho jayengi.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "youtu" not in url: return
    
    status = await update.message.reply_text("🚀 **Bypassing Region Locks & Analyzing...**", parse_mode="Markdown")
    
    # yt-dlp Options with Cookie & Bypass Logic
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'cookiefile': 'cookies.txt', # Workflow ise create karega
        'geo_bypass': True,
        'geo_bypass_country': 'IN', # Indian content ke liye
        'quiet': False,
        'no_warnings': False,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'outtmpl': f'downloads/%(id)s.%(ext)s',
        'progress_hooks': [lambda d: progress_hook(d, context, update.effective_chat.id, status.message_id)],
    }

    try:
        if not os.path.exists('downloads'): os.makedirs('downloads')
        
        with YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp4'

        await status.edit_text("⬆️ **Uploading Original Quality (Document)...**", parse_mode="Markdown")
        
        with open(path, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                caption=f"✅ {info.get('title', 'Video')}\n🌟 Quality: Original",
                write_timeout=300
            )
        os.remove(path)
        await status.delete()
        
    except Exception as e:
        await status.edit_text(f"❌ **Error:**\n`{str(e)}`", parse_mode="Markdown")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
