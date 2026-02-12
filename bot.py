import os
import telebot
from telebot import types
import yt_dlp

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

social_wait = {}
yt_wait = {}

DOWNLOAD_DIR = "/tmp"

# -------------------------
# بررسی عضویت
# -------------------------
def is_member(user_id):
    if not CHANNEL_USERNAME:
        return True
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

def join_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "🔗 عضویت در کانال",
        url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"
    ))
    kb.add(types.InlineKeyboardButton(
        "✅ بررسی عضویت",
        callback_data="check_join"
    ))
    return kb

# -------------------------
# دانلود لینک (ویدیو / آهنگ)
# -------------------------
def download(url, audio=False, quality=None):
    if audio:
        opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
            "noplaylist": True,
            "quiet": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"
            }]
        }
    elif quality:
        opts = {
            "format": f"bestvideo[height<={quality}]+bestaudio/best",
            "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
            "merge_output_format": "mp4",
            "noplaylist": True,
            "quiet": True
        }
    else:
        opts = {
            "format": "best",
            "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
            "noplaylist": True,
            "quiet": True
        }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file = ydl.prepare_filename(info)
        if audio:
            return file.rsplit(".", 1)[0] + ".mp3"
        return file

# -------------------------
# ✅ دانلود آهنگ کامل با سرچ (FULL SONG)
# -------------------------
def download_full_song(query):
    opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "noplaylist": True,
        "quiet": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    }

    search_query = f"ytsearch1:{query} official audio full song"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(search_query, download=True)
        entry = info["entries"][0]
        file = ydl.prepare_filename(entry)
        return file.rsplit(".", 1)[0] + ".mp3"

# -------------------------
# start
# -------------------------
@bot.message_handler(commands=["start"])
def start(m):
    if not is_member(m.from_user.id):
        bot.send_message(m.chat.id, "❗ عضو کانال شو", reply_markup=join_keyboard())
        return
    bot.send_message(
        m.chat.id,
        "✅ لینک ویدیو بفرست\n"
        "🎵 یا اسم آهنگ / خواننده رو بفرست (آهنگ کامل MP3)"
    )

# -------------------------
# بررسی عضویت
# -------------------------
@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join(c):
    if is_member(c.from_user.id):
        bot.answer_callback_query(c.id, "✅ تأیید شد")
        bot.send_message(c.message.chat.id, "حالا ادامه بده ✅")
    else:
        bot.answer_callback_query(c.id, "❌ هنوز عضو نیستی", show_alert=True)

# -------------------------
# انتخاب شبکه‌های اجتماعی
# -------------------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("social_"))
def social_choice(c):
    user_id = c.from_user.id
    bot.answer_callback_query(c.id, "⏳ در حال پردازش...")

    if user_id not in social_wait:
        bot.send_message(c.message.chat.id, "❌ لینک منقضی شده")
        return

    url = social_wait.pop(user_id)
    choice = c.data.split("_")[1]

    try:
        if choice in ["video", "both"]:
            v = download(url)
            with open(v, "rb") as f:
                bot.send_video(c.message.chat.id, f)

        if choice in ["audio", "both"]:
            a = download(url, audio=True)
            with open(a, "rb") as f:
                bot.send_audio(c.message.chat.id, f)

    except:
        bot.send_message(c.message.chat.id, "❌ خطا در دانلود")

# -------------------------
# انتخاب کیفیت یوتیوب
# -------------------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("yt_"))
def yt_choice(c):
    user_id = c.from_user.id
    bot.answer_callback_query(c.id, "⏳ در حال پردازش...")

    if user_id not in yt_wait:
        bot.send_message(c.message.chat.id, "❌ لینک منقضی شده")
        return

    url = yt_wait.pop(user_id)
    q = c.data.split("_")[1]

    try:
        if q == "audio":
            f = download(url, audio=True)
            with open(f, "rb") as a:
                bot.send_audio(c.message.chat.id, a)
        else:
            f = download(url, quality=q)
            with open(f, "rb") as v:
                bot.send_video(c.message.chat.id, v)

    except:
        bot.send_message(c.message.chat.id, "❌ خطا در دانلود")

# -------------------------
# پیام اصلی
# -------------------------
@bot.message_handler(func=lambda m: True)
def handle(m):
    if not is_member(m.from_user.id):
        bot.send_message(m.chat.id, "❗ عضو کانال شو", reply_markup=join_keyboard())
        return

    text = m.text.strip()

    # ✅ یوتیوب
    if "youtube.com" in text or "youtu.be" in text:
        yt_wait[m.from_user.id] = text
        kb = types.InlineKeyboardMarkup()
        for q in ["360", "480", "720", "1080"]:
            kb.add(types.InlineKeyboardButton(f"🎬 {q}p", callback_data=f"yt_{q}"))
        kb.add(types.InlineKeyboardButton("🎵 فقط آهنگ", callback_data="yt_audio"))
        bot.send_message(m.chat.id, "کیفیت رو انتخاب کن:", reply_markup=kb)
        return

    # ✅ اینستاگرام / تیک‌تاک / پینترست
    if any(x in text for x in ["instagram.com", "tiktok.com", "pinterest"]):
        social_wait[m.from_user.id] = text
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🎬 فقط ویدیو", callback_data="social_video"))
        kb.add(types.InlineKeyboardButton("🎵 فقط آهنگ", callback_data="social_audio"))
        kb.add(types.InlineKeyboardButton("🎬🎵 ویدیو + آهنگ", callback_data="social_both"))
        bot.send_message(m.chat.id, "چی می‌خوای؟", reply_markup=kb)
        return

    # ✅ اگر لینک نبود → اسم آهنگ
    msg = bot.send_message(m.chat.id, "🔍 در حال پیدا کردن آهنگ کامل...")

    try:
        song = download_full_song(text)
        with open(song, "rb") as a:
            bot.send_audio(
                m.chat.id,
                a,
                caption="✅ <b>آهنگ کامل ارسال شد</b>"
            )
    except:
        bot.send_message(m.chat.id, "❌ آهنگ پیدا نشد")

# -------------------------
print("Bot started...")
bot.infinity_polling()
