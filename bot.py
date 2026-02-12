import os
import telebot
from telebot import types
import yt_dlp

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

DOWNLOAD_DIR = "/tmp"
social_wait = {}
yt_wait = {}

# =========================
# ✅ Instagram Cookies
# =========================
IG_COOKIE_FILE = "/tmp/ig.txt"

if os.getenv("IG_COOKIES"):
    with open(IG_COOKIE_FILE, "w", encoding="utf-8") as f:
        f.write(os.getenv("IG_COOKIES"))

# =========================
# عضویت
# =========================
def is_member(uid):
    if not CHANNEL_USERNAME:
        return True
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, uid)
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

# =========================
# 🔍 سرچ آهنگ کامل
# =========================
def search_full_youtube(query):
    opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        res = ydl.extract_info(
            f"ytsearch10:{query} official audio",
            download=False
        )

    valid = []
    for v in res["entries"]:
        title = (v.get("title") or "").lower()
        dur = v.get("duration") or 0

        if dur < 150:
            continue
        if any(x in title for x in ["short", "live", "remix", "cover"]):
            continue

        valid.append(v)

    if not valid:
        raise Exception("NO_FULL_VERSION")

    best = max(valid, key=lambda x: x["duration"])
    return f"https://www.youtube.com/watch?v={best['id']}"

# =========================
# ⬇️ Downloaders
# =========================
def base_opts(extra=None):
    opts = {
        "quiet": True,
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
    }
    if extra:
        opts.update(extra)
    return opts

def download_audio(url, instagram=False):
    opts = base_opts({
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    })

    if instagram and os.path.exists(IG_COOKIE_FILE):
        opts["cookiefile"] = IG_COOKIE_FILE

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        f = ydl.prepare_filename(info)
        return f.rsplit(".", 1)[0] + ".mp3"

def download_video(url, quality=None, instagram=False):
    fmt = f"bestvideo[height<={quality}]+bestaudio/best" if quality else "bestvideo+bestaudio/best"

    opts = base_opts({
        "format": fmt,
        "merge_output_format": "mp4"
    })

    if instagram and os.path.exists(IG_COOKIE_FILE):
        opts["cookiefile"] = IG_COOKIE_FILE

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# =========================
# START
# =========================
@bot.message_handler(commands=["start"])
def start(m):
    if not is_member(m.from_user.id):
        bot.send_message(m.chat.id, "❗ عضو کانال شو", reply_markup=join_keyboard())
        return
    bot.send_message(m.chat.id, "✅ لینک بفرست یا اسم آهنگ")

@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join(c):
    if is_member(c.from_user.id):
        bot.answer_callback_query(c.id, "✅ تایید شد")
        bot.send_message(c.message.chat.id, "ادامه بده ✅")
    else:
        bot.answer_callback_query(c.id, "❌ هنوز عضو نیستی", show_alert=True)

# =========================
# Callbacks
# =========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("yt_"))
def yt_choice(c):
    uid = c.from_user.id
    bot.answer_callback_query(c.id, "⏳")

    if uid not in yt_wait:
        bot.send_message(c.message.chat.id, "❌ لینک منقضی شد")
        return

    url = yt_wait.pop(uid)
    q = c.data.split("_")[1]

    try:
        if q == "audio":
            f = download_audio(url)
            bot.send_audio(c.message.chat.id, open(f, "rb"))
        else:
            f = download_video(url, q)
            bot.send_video(c.message.chat.id, open(f, "rb"))
    except:
        bot.send_message(c.message.chat.id, "❌ خطا در دانلود")

@bot.callback_query_handler(func=lambda c: c.data.startswith("social_"))
def social_choice(c):
    uid = c.from_user.id
    bot.answer_callback_query(c.id, "⏳")

    if uid not in social_wait:
        bot.send_message(c.message.chat.id, "❌ لینک منقضی شد")
        return

    url = social_wait.pop(uid)
    ch = c.data.split("_")[1]
    is_ig = "instagram.com" in url

    try:
        if ch in ["video", "both"]:
            v = download_video(url, instagram=is_ig)
            bot.send_video(c.message.chat.id, open(v, "rb"))
        if ch in ["audio", "both"]:
            a = download_audio(url, instagram=is_ig)
            bot.send_audio(c.message.chat.id, open(a, "rb"))
    except:
        bot.send_message(
            c.message.chat.id,
            "❌ دانلود این لینک نیاز به لاگین اینستاگرام دارد"
        )

# =========================
# MESSAGE
# =========================
@bot.message_handler(func=lambda m: True)
def handle(m):
    if not is_member(m.from_user.id):
        bot.send_message(m.chat.id, "❗ عضو کانال شو", reply_markup=join_keyboard())
        return

    text = m.text.strip()

    if "youtube.com" in text or "youtu.be" in text:
        yt_wait[m.from_user.id] = text
        kb = types.InlineKeyboardMarkup()
        for q in ["360", "480", "720", "1080"]:
            kb.add(types.InlineKeyboardButton(f"{q}p 🎬", callback_data=f"yt_{q}"))
        kb.add(types.InlineKeyboardButton("🎵 فقط آهنگ", callback_data="yt_audio"))
        bot.send_message(m.chat.id, "کیفیت رو انتخاب کن:", reply_markup=kb)
        return

    if any(x in text for x in ["instagram.com", "tiktok.com", "pinterest"]):
        social_wait[m.from_user.id] = text
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🎬 ویدیو", callback_data="social_video"))
        kb.add(types.InlineKeyboardButton("🎵 آهنگ", callback_data="social_audio"))
        kb.add(types.InlineKeyboardButton("🎬🎵 هر دو", callback_data="social_both"))
        bot.send_message(m.chat.id, "انتخاب کن:", reply_markup=kb)
        return

    bot.send_message(m.chat.id, "🔍 در حال پیدا کردن نسخه کامل...")

    try:
        url = search_full_youtube(text)
        song = download_audio(url)
        bot.send_audio(m.chat.id, open(song, "rb"), caption="✅ آهنگ کامل")
    except:
        bot.send_message(m.chat.id, "❌ نسخه کامل پیدا نشد")

print("✅ BOT RUNNING")
bot.infinity_polling()
