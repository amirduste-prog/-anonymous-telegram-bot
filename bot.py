import os
import telebot
import yt_dlp
from telebot import types

# ================== ENV ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

DOWNLOAD_DIR = "/tmp"
USERS_FILE = "/tmp/users.txt"

# ================== USER SAVE ==================
def save_user(u):
    users = {}

    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                uid, name = line.strip().split("|")
                users[uid] = line.strip()

    users[str(u.id)] = f"{u.id}|{u.first_name}"

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(users.values()))

# ================== FULL SONG SEARCH (FIXED) ==================
def download_full_song(query):
    search_opts = {
        "quiet": True,
        "skip_download": True
    }

    with yt_dlp.YoutubeDL(search_opts) as ydl:
        res = ydl.extract_info(f"ytsearch10:{query}", download=False)

    candidates = []

    for e in res.get("entries", []):
        if not e or not e.get("id"):
            continue

        try:
            with yt_dlp.YoutubeDL({"quiet": True}) as ydl2:
                info = ydl2.extract_info(
                    f"https://www.youtube.com/watch?v={e['id']}",
                    download=False
                )
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
        raise Exception("NO_FULL_SONG")

    best = max(candidates, key=lambda x: x["duration"])

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
        info = ydl.extract_info(best["webpage_url"], download=True)
        file = ydl.prepare_filename(info)

    return file.rsplit(".", 1)[0] + ".mp3"

# ================== START ==================
@bot.message_handler(commands=["start"])
def start(m):
    save_user(m.from_user)
    bot.send_message(m.chat.id, "🎵 لینک یا اسم آهنگ رو بفرست")

# ================== ADMIN MEMBER ==================
@bot.message_handler(func=lambda m: m.text == "#member")
def members(m):
    if m.from_user.id != ADMIN_ID:
        return

    if not os.path.exists(USERS_FILE):
        bot.send_message(m.chat.id, "❌ هنوز کاربری ثبت نشده")
        return

    with open(USERS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    text = f"👥 <b>تعداد اعضا:</b> {len(lines)}\n\n"
    for line in lines:
        uid, name = line.strip().split("|")
        text += f"👤 {name} | <code>{uid}</code>\n"

    bot.send_message(m.chat.id, text)

# ================== MAIN HANDLER ==================
@bot.message_handler(func=lambda m: True)
def handle(m):
    save_user(m.from_user)
    text = m.text.strip()

    bot.send_message(m.chat.id, "🔍 در حال پیدا کردن نسخه کامل...")

    try:
        song = download_full_song(text)
        with open(song, "rb") as a:
            bot.send_audio(m.chat.id, a, caption="✅ آهنگ کامل")
    except:
        bot.send_message(m.chat.id, "❌ آهنگ کامل پیدا نشد")

# ================== RUN ==================
print("✅ BOT IS RUNNING")
bot.infinity_polling()
