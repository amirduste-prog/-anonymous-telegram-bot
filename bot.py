import os
import telebot
from telebot import types
import yt_dlp

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

DOWNLOAD_DIR = "/tmp"
USERS_FILE = "/tmp/users.txt"

social_wait = {}
yt_wait = {}

# -------------------------
# ذخیره کاربران
# -------------------------
def save_user(u):
    users = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                uid, name, username = line.strip().split("|")
                users[uid] = line.strip()

    users[str(u.id)] = f"{u.id}|{u.first_name}|{u.username or '-'}"

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(users.values()))

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
# دانلود مستقیم
# -------------------------
def download(url, audio=False, quality=None):
    opts = {
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "quiet": True,
        "noplaylist": True
    }

    if audio:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    elif quality:
        opts["format"] = f"bestvideo[height<={quality}]+bestaudio/best"
        opts["merge_output_format"] = "mp4"
    else:
        opts["format"] = "best"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file = ydl.prepare_filename(info)
        return file.rsplit(".", 1)[0] + ".mp3" if audio else file

# -------------------------
# ✅ سرچ حرفه‌ای آهنگ کامل (BUG FIXED)
# -------------------------
def download_full_song(query):
    search_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True
    }

    with yt_dlp.YoutubeDL(search_opts) as ydl:
        res = ydl.extract_info(f"ytsearch10:{query}", download=False)

    valid = []
    for v in res.get("entries", []):
        title = (v.get("title") or "").lower()
        dur = v.get("duration") or 0

        if dur < 150:
            continue
        if any(x in title for x in ["short", "live", "remix", "cover"]):
            continue

        valid.append(v)

    if not valid:
        raise Exception("NO_FULL_SONG")

    best = max(valid, key=lambda x: x["duration"])
    url = f"https://www.youtube.com/watch?v={best['id']}"

    opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file = ydl.prepare_filename(info)
        return file.rsplit(".", 1)[0] + ".mp3"

# -------------------------
# start
# -------------------------
@bot.message_handler(commands=["start"])
def start(m):
    save_user(m.from_user)
    if not is_member(m.from_user.id):
        bot.send_message(m.chat.id, "❗ عضو کانال شو", reply_markup=join_keyboard())
        return
    bot.send_message(m.chat.id, "✅ لینک بفرست یا اسم آهنگ")

# -------------------------
# admin member
# -------------------------
@bot.message_handler(func=lambda m: m.text == "member")
def members(m):
    if m.from_user.id != ADMIN_ID:
        return

    if not os.path.exists(USERS_FILE):
        bot.send_message(m.chat.id, "❌ کاربری ثبت نشده")
        return

    with open(USERS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    text = f"👥 <b>تعداد کاربران:</b> {len(lines)}\n\n"
    for l in lines:
        uid, name, username = l.strip().split("|")
        text += f"👤 {name} | @{username} | <code>{uid}</code>\n"

    bot.send_message(m.chat.id, text)

# -------------------------
# callback join
# -------------------------
@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join(c):
    if is_member(c.from_user.id):
        bot.answer_callback_query(c.id, "✅ تأیید شد")
        bot.send_message(c.message.chat.id, "ادامه بده ✅")
    else:
        bot.answer_callback_query(c.id, "❌ هنوز عضو نیستی", show_alert=True)

# -------------------------
# پیام اصلی
# -------------------------
@bot.message_handler(func=lambda m: True)
def handle(m):
    save_user(m.from_user)

    if not is_member(m.from_user.id):
        bot.send_message(m.chat.id, "❗ عضو کانال شو", reply_markup=join_keyboard())
        return

    text = m.text.strip()

    # یوتیوب
    if "youtube.com" in text or "youtu.be" in text:
        yt_wait[m.from_user.id] = text
        kb = types.InlineKeyboardMarkup()
        for q in ["360", "480", "720", "1080"]:
            kb.add(types.InlineKeyboardButton(f"{q}p 🎬", callback_data=f"yt_{q}"))
        kb.add(types.InlineKeyboardButton("🎵 فقط آهنگ", callback_data="yt_audio"))
        bot.send_message(m.chat.id, "کیفیت رو انتخاب کن:", reply_markup=kb)
        return

    # شبکه اجتماعی
    if any(x in text for x in ["instagram.com", "tiktok.com", "pinterest"]):
        social_wait[m.from_user.id] = text
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🎬 ویدیو", callback_data="social_video"))
        kb.add(types.InlineKeyboardButton("🎵 آهنگ", callback_data="social_audio"))
        kb.add(types.InlineKeyboardButton("🎬🎵 هر دو", callback_data="social_both"))
        bot.send_message(m.chat.id, "انتخاب کن:", reply_markup=kb)
        return

    # اسم آهنگ یا لینک → سرچ گوگل‌مانند
    bot.send_message(m.chat.id, "🔍 در حال پیدا کردن نسخه کامل...")
    try:
        song = download_full_song(text)
        bot.send_audio(m.chat.id, open(song, "rb"), caption="✅ آهنگ کامل")
    except:
        bot.send_message(m.chat.id, "❌ آهنگ کامل پیدا نشد")

print("✅ BOT RUNNING")
bot.infinity_polling()
