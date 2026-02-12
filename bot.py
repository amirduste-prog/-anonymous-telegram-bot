import os
import telebot
import yt_dlp
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# -------------------------
# دانلود آهنگ کامل
# -------------------------
def download_full_song(query):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "noplaylist": True,
        "quiet": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            f"ytsearch1:{query} official audio full song",
            download=True
        )
        entry = info["entries"][0]
        filename = ydl.prepare_filename(entry)
        return filename.rsplit(".", 1)[0] + ".mp3"

# -------------------------
# استارت
# -------------------------
@bot.message_handler(commands=["start"])
def start(msg):
    bot.send_message(
        msg.chat.id,
        "🎵 <b>اسم آهنگ یا اسم خواننده رو بفرست</b>\n\n"
        "✅ آهنگ کامل MP3 ارسال میشه\n❌ نه تیکه ❌"
    )

# -------------------------
# دریافت متن (اسم آهنگ)
# -------------------------
@bot.message_handler(content_types=["text"])
def handle_song(msg):
    query = msg.text.strip()

    status = bot.send_message(
        msg.chat.id,
        "🔍 در حال پیدا کردن آهنگ کامل..."
    )

    try:
        song_path = download_full_song(query)

        with open(song_path, "rb") as audio:
            bot.send_audio(
                msg.chat.id,
                audio,
                caption="✅ <b>آهنگ کامل ارسال شد</b>"
            )

        os.remove(song_path)

    except Exception as e:
        bot.send_message(
            msg.chat.id,
            f"❌ خطا در دانلود:\n<code>{e}</code>"
        )

# -------------------------
# اجرا
# -------------------------
print("Bot started...")
bot.infinity_polling()
