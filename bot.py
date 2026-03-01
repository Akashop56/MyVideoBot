import os, asyncio, logging, time, base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from yt_dlp import YoutubeDL

# Logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TG_TOKEN")
user_settings = {} # Store: {user_id: {"q": "best", "timer": 5}}

# Progress Hook
def progress_hook(d, context, chat_id, message_id):
    if d['status'] == 'downloading':
        p = d.get('_percent_str', '0%')
        s = d.get('_speed_str', '0B/s')
        e = d.get('_eta_str', '00:00')
        prog_text = f"⬇️ **Downloading...**\n━━━━━━━━━━━━\n📊 Progress: {p}\n🚀 Speed: {s}\n⏳ ETA: {e}"
        try:
            asyncio.run_coroutine_threadsafe(
                context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=prog_text, parse_mode="Markdown"),
                context.application.loop
            )
        except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello Akash! YouTube link bhejo ya naam likh kar search karo.\nUse /settings for quality.")

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎬 Default Quality", callback_data="set_q")],
        [InlineKeyboardButton("🧹 Cleanup Timer", callback_data="set_c")],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ]
    await update.message.reply_text("⚙️ **Settings Menu**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    if uid not in user_settings: user_settings[uid] = {"q": "best", "timer": 5}

    if query.data == "set_q":
        keys = [[InlineKeyboardButton(f"{r}p", callback_data=f"q_{r}")] for r in ["360", "480", "720", "1080", "best"]]
        await query.edit_message_text("Select Video Quality:", reply_markup=InlineKeyboardMarkup(keys))
    elif query.data.startswith("q_"):
        user_settings[uid]["q"] = query.data.split("_")[1]
        await query.edit_message_text(f"✅ Quality set to {user_settings[uid]['q']}")
    elif query.data == "close":
        await query.message.delete()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    if uid not in user_settings: user_settings[uid] = {"q": "best", "timer": 5}

    # Search or URL?
    if "youtu" in text:
        url = text
    else:
        # Search Flow
        status = await update.message.reply_text(f"🔎 Searching for: {text}...")
        with YoutubeDL({'quiet': True, 'cookiefile': 'cookies.txt'}) as ydl:
            res = await asyncio.to_thread(ydl.extract_info, f"ytsearch1:{text}", download=False)
            if not res['entries']:
                await status.edit_text("❌ No results found."); return
            url = res['entries'][0]['webpage_url']
            await status.delete()

    # Format Selection
    q = user_settings[uid]["q"]
    f_str = "bestvideo+bestaudio/best" if q == "best" else f"bestvideo[height<={q}]+bestaudio/best"

    status = await update.message.reply_text("🚀 **Bypassing Region Locks...**", parse_mode="Markdown")
    
    ydl_opts = {
        'format': f_str,
        'merge_output_format': 'mp4',
        'cookiefile': 'cookies.txt',
        'geo_bypass': True,
        'geo_bypass_country': 'IN',
        'outtmpl': f'downloads/{uid}_%(id)s.%(ext)s',
        'progress_hooks': [lambda d: progress_hook(d, context, update.effective_chat.id, status.message_id)],
    }

    try:
        if not os.path.exists('downloads'): os.makedirs('downloads')
        with YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp4'

        await status.edit_text("⬆️ **Uploading Document (Original Quality)...**", parse_mode="Markdown")
        with open(path, 'rb') as f:
            await context.bot.send_document(chat_id=update.effective_chat.id, document=f, 
                                          caption=f"✅ {info['title']}\n🌟 Quality: {q}", 
                                          reply_to_message_id=update.message.message_id)
        
        await status.delete()
        os.remove(path)
    except Exception as e:
        await status.edit_text(f"❌ **Error:**\n`{str(e)}`", parse_mode="Markdown")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
