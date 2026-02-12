import os
import telebot
from telebot import types
import yt_dlp
import requests

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
    if CHANNEL_USERNAME:
        kb.add(types.InlineKeyboardButton("🔗 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"))
    kb.add(types.InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_join"))
    return kb

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

# ========= CALLBACK =========
@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join(c):
    if is_member(c.from_user.id):
        bot.answer_callback_query(c.id, "✅ عضویت تأیید شد")
        bot.send_message(c.message.chat.id, "حالا لینک رو بفرست ✅")
    else:
        bot.answer_callback_query(c.id, "❌ هنوز عضو نیستی", show_alert=True)

# ========= ADMIN =========
@bot.message_handler(commands=["member"])
def members(m):
    if m.from_user.id != ADMIN_ID:
        return

    try:
        chat = bot.get_chat(CHANNEL_USERNAME)
        count = chat.get_member_count()
        bot.send_message(m.chat.id, f"👥 تعداد اعضا: {count}")
    except Exception as e:
        bot.send_message(m.chat.id, f"خطا: {e}")

# ========= DOWNLOAD =========
def download_media(url, audio=False):
    opts = {
        "outtmpl": "/tmp/%(title)s.%(ext)s",
        "format": "bestaudio/best" if audio else "best",
        "quiet": True
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return filename

# ========= YOUTUBE ASK =========
user_waiting = {}

@bot.message_handler(func=lambda m: True)
def handle(m):
    if not is_member(m.from_user.id):
        bot.send_message(m.chat.id, "❗ عضو کانال شو", reply_markup=join_keyboard())
        return

    text = m.text.strip()

    # Waiting for YouTube choice
    if m.from_user.id in user_waiting:
        url = user_waiting.pop(m.from_user.id)
        audio = text == "🎵 آهنگ"
        file = download_media(url, audio)
        with open(file, "rb") as f:
            if audio:
                bot.send_audio(m.chat.id, f)
            else:
                bot.send_video(m.chat.id, f)
        return

    # YouTube
    if "youtube.com" in text or "youtu.be" in text:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add("🎵 آهنگ", "🎬 ویدیو")
        user_waiting[m.from_user.id] = text
        bot.send_message(m.chat.id, "چی می‌خوای؟", reply_markup=kb)
        return

    # Instagram / TikTok / Pinterest
    if any(x in text for x in ["instagram.com", "tiktok.com", "pinterest"]):
        file = download_media(text, audio=False)
        with open(file, "rb") as f:
            bot.send_video(m.chat.id, f)
        return

    bot.send_message(m.chat.id, "❌ لینک معتبر نیست")

# ========= RUN =========
bot.infinity_polling()
