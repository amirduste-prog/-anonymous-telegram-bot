import os
import telebot
from telebot import types
import yt_dlp

# ================== ENV ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # @channel
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

DOWNLOAD_DIR = "/tmp"
USERS_FILE = "/tmp/users.txt"

social_wait = {}
yt_wait = {}

# ================== SAVE USER ==================
def save_user(u):
    users = {}

    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                uid, name, username = line.strip().split("|")
                users[uid] = line.strip()

    username = u.username if u.username else "-"
    users[str(u.id)] = f"{u.id}|{u.first_name}|{username}"

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(users.values()))

# ================== CHECK MEMBER CHANNEL ==================
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

# ================== DOWNLOAD ==================
def download(url, audio=False, quality=None):
    if audio:
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
    elif quality:
        opts = {
            "format": f"bestvideo[height<={quality}]+bestaudio/best",
            "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
            "merge_output_format": "mp4",
            "quiet": True,
            "noplaylist": True
        }
    else:
        opts = {
            "format": "best",
            "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
            "quiet": True,
            "noplaylist": True
        }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file = ydl.prepare_filename(info)

    return file.rsplit(".", 1)[0] + ".mp3" if audio else file

# ================== FULL SONG SEARCH ==================
def download_full_song(query):
    with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
        res = ydl.extract_info(f"ytsearch10:{query}", download=False)

    candidates = []
    for e in res.get("entries", []):
        try:
            with yt_dlp.YoutubeDL({"quiet": True}) as y:
                info = y.extract_info(e["webpage_url"], download=False)
        except:
            continue

        title = (info.get("title") or "").lower()
        duration = info.get("duration") or 0

        if duration < 150:
            continue
        if any(x in title for x in ["live", "remix", "cover", "short", "sped up"]):
            continue

        candidates.append(info)

    if not candidates:
        raise Exception("NO_SONG")

    best = max(candidates, key=lambda x: x["duration"])

    opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "quiet": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(best["webpage_url"], download=True)
        file = ydl.prepare_filename(info)

    return file.rsplit(".", 1)[0] + ".mp3"

# ================== START ==================
@bot.message_handler(commands=["start"])
def start(m):
    save_user(m.from_user)

    if not is_member(m.from_user.id):
        bot.send_message(m.chat.id, "❗ ابتدا عضو کانال شو", reply_markup=join_keyboard())
        return

    bot.send_message(
        m.chat.id,
        "✅ لینک بفرست (یوتیوب / اینستاگرام / تیک‌تاک)\n"
        "🎵 یا اسم آهنگ برای MP3 کامل"
    )

# ================== CHECK JOIN ==================
@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join(c):
    if is_member(c.from_user.id):
        bot.answer_callback_query(c.id, "✅ تأیید شد")
        bot.send_message(c.message.chat.id, "حالا ادامه بده ✅")
    else:
        bot.answer_callback_query(c.id, "❌ هنوز عضو نیستی", show_alert=True)

# ================== ADMIN #member ==================
@bot.message_handler(func=lambda m: m.text == "#member")
def members(m):
    if m.from_user.id != ADMIN_ID:
        return

    if not os.path.exists(USERS_FILE):
        bot.send_message(m.chat.id, "❌ کاربری ثبت نشده")
        return

    with open(USERS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    text = f"👥 <b>تعداد اعضا:</b> {len(lines)}\n\n"
    for line in lines:
        uid, name, username = line.strip().split("|")
        text += f"👤 {name} (@{username}) | <code>{uid}</code>\n"

    bot.send_message(m.chat.id, text)

# ================== CALLBACKS ==================
@bot.callback_query_handler(func=lambda c: c.data.startswith("social_"))
def social_choice(c):
    uid = c.from_user.id
    if uid not in social_wait:
        return

    url = social_wait.pop(uid)
    choice = c.data.split("_")[1]

    try:
        if choice in ["video", "both"]:
            v = download(url)
            bot.send_video(c.message.chat.id, open(v, "rb"))

        if choice in ["audio", "both"]:
            a = download(url, audio=True)
            bot.send_audio(c.message.chat.id, open(a, "rb"))
    except:
        bot.send_message(c.message.chat.id, "❌ خطا در دانلود")

@bot.callback_query_handler(func=lambda c: c.data.startswith("yt_"))
def yt_choice(c):
    uid = c.from_user.id
    if uid not in yt_wait:
        return

    url = yt_wait.pop(uid)
    q = c.data.split("_")[1]

    try:
        if q == "audio":
            f = download(url, audio=True)
            bot.send_audio(c.message.chat.id, open(f, "rb"))
        else:
            f = download(url, quality=q)
            bot.send_video(c.message.chat.id, open(f, "rb"))
    except:
        bot.send_message(c.message.chat.id, "❌ خطا در دانلود")

# ================== MAIN HANDLER ==================
@bot.message_handler(func=lambda m: True)
def handle(m):
    save_user(m.from_user)

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
        bot.send_message(m.chat.id, "چی می‌خوای؟", reply_markup=kb)
        return

    bot.send_message(m.chat.id, "🔍 در حال پیدا کردن آهنگ کامل...")
    try:
        song = download_full_song(text)
        bot.send_audio(m.chat.id, open(song, "rb"), caption="✅ آهنگ کامل")
    except:
        bot.send_message(m.chat.id, "❌ آهنگ پیدا نشد")

# ================== RUN ==================
print("✅ Bot started")
bot.infinity_polling()
