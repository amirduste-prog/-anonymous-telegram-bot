import os
import telebot
from telebot import types
import yt_dlp

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

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
    kb.add(types.InlineKeyboardButton("🔗 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"))
    kb.add(types.InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_join"))
    return kb

def download(url, audio=False, quality=None):
    if audio:
        opts = {
            "format": "bestaudio/best",
            "outtmpl": "/tmp/%(title)s.%(ext)s",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"
            }],
            "quiet": True
        }
    elif quality:
        opts = {
            "format": f"bestvideo[height<={quality}]+bestaudio/best",
            "outtmpl": "/tmp/%(title)s.%(ext)s",
            "merge_output_format": "mp4",
            "quiet": True
        }
    else:
        opts = {
            "format": "best",
            "outtmpl": "/tmp/%(title)s.%(ext)s",
            "quiet": True
        }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if audio:
            return filename.rsplit(".", 1)[0] + ".mp3"
        return filename

social_wait = {}
yt_wait = {}

@bot.message_handler(commands=["start"])
def start(m):
    if not is_member(m.from_user.id):
        bot.send_message(m.chat.id, "❗ برای استفاده ابتدا عضو کانال شوید", reply_markup=join_keyboard())
        return
    bot.send_message(m.chat.id, "✅ لینک اینستاگرام، تیک‌تاک، پینترست یا یوتیوب رو بفرست")

@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join(c):
    if is_member(c.from_user.id):
        bot.answer_callback_query(c.id, "✅ عضویت تأیید شد")
        bot.send_message(c.message.chat.id, "حالا لینک رو بفرست ✅")
    else:
        bot.answer_callback_query(c.id, "❌ هنوز عضو نیستی", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("social_"))
def social_choice(c):
    url = social_wait.pop(c.from_user.id)
    choice = c.data.split("_")[1]

    if choice in ["video", "both"]:
        v = download(url)
        with open(v, "rb") as f:
            bot.send_video(c.message.chat.id, f)

    if choice in ["audio", "both"]:
        a = download(url, audio=True)
        with open(a, "rb") as f:
            bot.send_audio(c.message.chat.id, f)

    bot.answer_callback_query(c.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("yt_"))
def yt_choice(c):
    url = yt_wait.pop(c.from_user.id)
    q = c.data.split("_")[1]

    if q == "audio":
        f = download(url, audio=True)
        with open(f, "rb") as a:
            bot.send_audio(c.message.chat.id, a)
    else:
        f = download(url, quality=q)
        with open(f, "rb") as v:
            bot.send_video(c.message.chat.id, v)

    bot.answer_callback_query(c.id)

@bot.message_handler(func=lambda m: True)
def handle(m):
    if not is_member(m.from_user.id):
        bot.send_message(m.chat.id, "❗ عضو کانال شو", reply_markup=join_keyboard())
        return

    text = m.text.strip()

    if "youtube.com" in text or "youtu.be" in text:
        yt_wait[m.from_user.id] = text
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🎬 360p", callback_data="yt_360"))
        kb.add(types.InlineKeyboardButton("🎬 480p", callback_data="yt_480"))
        kb.add(types.InlineKeyboardButton("🎬 720p", callback_data="yt_720"))
        kb.add(types.InlineKeyboardButton("🎬 1080p", callback_data="yt_1080"))
        kb.add(types.InlineKeyboardButton("🎵 فقط آهنگ", callback_data="yt_audio"))
        bot.send_message(m.chat.id, "کیفیت رو انتخاب کن:", reply_markup=kb)
        return

    if any(x in text for x in ["instagram.com", "tiktok.com", "pinterest"]):
        social_wait[m.from_user.id] = text
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🎬 فقط ویدیو", callback_data="social_video"))
        kb.add(types.InlineKeyboardButton("🎵 فقط آهنگ", callback_data="social_audio"))
        kb.add(types.InlineKeyboardButton("🎬🎵 ویدیو + آهنگ", callback_data="social_both"))
        bot.send_message(m.chat.id, "انتخاب کن:", reply_markup=kb)
        return

    bot.send_message(m.chat.id, "❌ لینک معتبر نیست")

bot.infinity_polling()
