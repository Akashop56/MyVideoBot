import os, asyncio, logging, random, requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup

# Logging & Config
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = os.getenv("TG_TOKEN")

# Rate limit bypass: User-Agents list
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

def get_live_stats(player_name):
    """Basic Scraping for recent match context (Free & No API Key)"""
    try:
        search_url = f"https://www.google.com/search?q={player_name.replace(' ', '+')}+last+match+score"
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        response = requests.get(search_url, headers=headers, timeout=5)
        # Yaha hum sirf snippet nikal rahe hain context ke liye
        soup = BeautifulSoup(response.text, 'html.parser')
        snippet = soup.find('div', class_='BNeawe').get_text() if soup.find('div', class_='BNeawe') else "No recent stats found"
        return snippet
    except:
        return "Stats temporary unavailable"

def search_image_safe(query):
    """Ratelimit handle karne ke liye try-except block"""
    try:
        with DDGS() as ddgs:
            # Random delay to avoid 403
            results = ddgs.images(f"{query} cricket hd", max_results=1)
            return results[0]['image'] if results else None
    except Exception as e:
        print(f"Search Error: {e}")
        return None

async def handle_poll_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    status = await update.message.reply_text("📊 Generating Pro Poll for SkyVerse...")

    # Multi-player logic: "Dhoni vs Rohit vs Kohli"
    players = [p.strip() for p in user_input.split("vs")]
    
    poll_text = f"🔥 **YOUTUBE COMMUNITY POLL** 🔥\n\n"
    poll_text += f"❓ **Question:** Who is performing better in this season?\n\n"
    
    images = []
    stats_summary = ""

    for i, name in enumerate(players[:3], 1): # Max 3 players for clarity
        img = await asyncio.to_thread(search_image_safe, name)
        stats = await asyncio.to_thread(get_live_stats, name)
        
        if img: images.append(img)
        poll_text += f"{i}️⃣ {name.title()}\n"
        stats_summary += f"🏏 **{name.title()} Context:** {stats[:100]}...\n"
        await asyncio.sleep(1) # Delay to prevent rate limit

    poll_text += f"4️⃣ Other (Comment below!)\n\n"
    poll_text += f"━━━━━━━━━━━━━\n{stats_summary}\n"
    poll_text += f"✨ *Copy-Paste to YouTube Community Tab!*"

    try:
        if images:
            # Pehli image ko main photo ki tarah bhejna
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=images[0],
                caption=poll_text,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(poll_text, parse_mode="Markdown")
        await status.delete()
    except Exception as e:
        await status.edit_text(f"❌ Error: {str(e)}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Bhejo players ke naam (e.g. Dhoni vs Rohit)")))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_poll_request))
    app.run_polling()

if __name__ == "__main__":
    main()
