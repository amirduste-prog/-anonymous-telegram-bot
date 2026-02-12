import os
import telebot
from telebot import types
import yt_dlp

# ========= ENV =========
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ========= MEMBERSHIP =========
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

# ========= DOWNLOAD =========
def download(url, audio=False, quality=None):
    if audio:
        fmt = "bestaudio/best"
    elif quality:
        fmt = f"bestvideo[height<={quality}]+bestaudio/best"
    else:
        fmt = "best"

    opts = {
        "format": fmt,
        "outtmpl": "/tmp/%(title)s.%(ext)s",
        "quiet": True
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# ========= STATES =========
social_wait = {}
yt_wait = {}

# ========= START =========
@bot.message_handler(commands=["start"])
def start(m):
    if not is_member(m.from_user.id):
        bot.send_message(
            m.chat.id,
            "❗ برای استفاده ابتدا عضو کانال شوید",
            reply_markup=join_keyboard()
        )
        return

    bot.send_message(
        m.chat.id,
        "✅ لینک اینستا، تیک‌تاک، پینترست یا یوتیوب رو بفرست"
    )

# ========= JOIN CHECK =========
@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join(c):
    if is_member(c.from_user.id):
        bot.answer_callback_query(c.id, "✅ عضویت تأیید شد")
        bot.send_message(c.message.chat.id, "حالا لینک رو بفرست ✅")
    else:
        bot.answer_callback_query(c.id, "❌ هنوز عضو نیستی", show_alert=True)

# ========= SOCIAL CALLBACK =========
@bot.callback_query_handler(func=lambda c: c.data.startswith("social_"))
def social_choice(c):
    choice = c.data.split("_")[1]
    url = social_wait.pop(c.from_user.id)

    if choice in ["video", "both"]:
        v = download(url)
        with open(v, "rb") as f:
            bot.send_video(c.message.chat.id, f)

    if choice in ["audio", "both"]:
        a = download(url, audio=True)
        with open(a, "rb") as f:
            bot.send_audio(c.message.chat.id, f)

    bot.answer_callback_query(c.id)

# ========= YOUTUBE CALLBACK =========
@bot.callback_query_handler(func=lambda c: c.data.startswith("yt_"))
def yt_choice(c):
    q = c.data.split("_")[1]
    url = yt_wait.pop(c.from_user.id)

    if q == "audio":
        f = download(url, audio=True)
        with open(f, "rb") as a:
            bot.send_audio(c.message.chat.id, a)
    else:
        f = download(url, quality=q)
        with open(f, "rb") as v:
            bot.send_video(c.message.chat.id, v)

    bot.answer_callback_query(c.id)

# ========= MESSAGE =========
@bot.message_handler(func=lambda m: True)
def handle(m):
    if not is_member(m.from_user.id):
        bot.send_message(m.chat.id, "❗ عضو کانال شو", reply_markup=join_keyboard())
        return

    text = m.text.strip()

    # YouTube
    if "youtube.com" in text or "youtu.be" in text:
        yt_wait[m.from_user.id] = text
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("🎬 360p", callback_data="yt_360"),
            types.InlineKeyboardButton("🎬 480p", callback_data="yt_480"),
            types.InlineKeyboardButton("🎬 720p", callback_data="yt_720"),
            types.InlineKeyboardButton("🎬 1080p", callback_data="yt_1080"),
            types.InlineKeyboardButton("🎵 فقط آهنگ", callback_data="yt_audio")
        )
        bot.send_message(m.chat.id, "کیفیت موردنظر رو انتخاب کن:", reply_markup=kb)
        return

    # Instagram / TikTok / Pinterest
    if any(x in text for x in ["instagram.com", "tiktok.com", "pinterest"]):
        social_wait[m.from_user.id] = text
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("🎬 فقط ویدیو", callback_data="social_video"),
            types.InlineKeyboardButton("🎵 فقط آهنگ", callback_data="social_audio"),
            types.InlineKeyboardButton("🎬🎵 ویدیو + آهنگ", callback_data="social_both")
        )
        bot.send_message(m.chat.id, "چی می‌خوای؟", reply_markup=kb)
        return

    bot.send_message(m.chat.id, "❌ لینک معتبر نیست")

# ========= RUN =========
bot.infinity_polling()
