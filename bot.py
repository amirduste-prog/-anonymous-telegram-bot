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
    if CHANNEL_USERNAME:
        kb.add(types.InlineKeyboardButton(
            "🔗 عضویت در کانال",
            url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"
        ))
    kb.add(types.InlineKeyboardButton(
        "✅ بررسی عضویت",
        callback_data="check_join"
    ))
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

# ========= CALLBACK JOIN =========
@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join(c):
    if is_member(c.from_user.id):
        bot.answer_callback_query(c.id, "✅ عضویت تأیید شد")
        bot.send_message(c.message.chat.id, "حالا لینک رو بفرست ✅")
    else:
        bot.answer_callback_query(c.id, "❌ هنوز عضو نیستی", show_alert=True)

# ========= ADMIN =========
@bot.message_handler(commands=["member"])
def member_cmd(m):
    if m.from_user.id != ADMIN_ID:
        return
    try:
        count = bot.get_chat(CHANNEL_USERNAME).get_member_count()
        bot.send_message(m.chat.id, f"👥 تعداد اعضا: {count}")
    except Exception as e:
        bot.send_message(m.chat.id, str(e))

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

# ========= YOUTUBE STATE =========
yt_wait = {}

# ========= CALLBACK QUALITY =========
@bot.callback_query_handler(func=lambda c: c.data.startswith("yt_"))
def yt_quality(c):
    q = c.data.split("_")[1]
    url = yt_wait.pop(c.from_user.id)

    if q == "audio":
        file = download
