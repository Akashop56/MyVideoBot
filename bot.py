import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from duckduckgo_search import DDGS

# Logging setup
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("TG_TOKEN")

# Function to search image for free
def search_image(query):
    with DDGS() as ddgs:
        # Player ki image search karna
        results = ddgs.images(query, max_results=1)
        if results:
            return results[0]['image']
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏏 **Cricket Poll Bot Active!**\n\n"
        "Bas player ka naam ya match topic likhein (e.g., 'Dhoni vs Kohli')\n"
        "Main aapko Image aur YouTube ke liye Poll Caption bana kar dunga."
    )

async def handle_poll_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = update.message.text
    status = await update.message.reply_text(f"🔍 Searching for '{topic}' images & data...")

    try:
        # 1. Image Search
        img_url = await asyncio.to_thread(search_image, f"{topic} cricket hd photo")
        
        if not img_url:
            await status.edit_text("❌ Image nahi mil payi. Kuch aur try karein.")
            return

        # 2. Automated Poll Captions (Creative logic)
        # Hum topic ke hisab se caption customize kar sakte hain
        poll_caption = (
            f"🔥 **YOUTUBE COMMUNITY POLL** 🔥\n\n"
            f"Topic: {topic}\n\n"
            f"❓ **Question:** Aapka kya maanna hai is match/player ke baare mein?\n\n"
            f"📊 **Options for YouTube:**\n"
            f"1️⃣ Masterclass Performance 🌟\n"
            f"2️⃣ Average/Theek-thaak 🏏\n"
            f"3️⃣ Bad Luck today 💔\n"
            f"4️⃣ Legend for a reason! 🐐\n\n"
            f"✨ *Direct copy-paste karein aur YouTube pe viral ho jayein!*"
        )

        # 3. Photo send karna
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=img_url,
            caption=poll_caption,
            parse_mode="Markdown"
        )
        await status.delete()

    except Exception as e:
        await status.edit_text(f"❌ Kuch error aaya: {str(e)}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_poll_request))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
