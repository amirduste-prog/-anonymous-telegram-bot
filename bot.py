import telebot
from telebot import types
import requests
import os
import json
import time
from datetime import datetime
from collections import defaultdict

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("GAPGPT_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
FORCE_CHANNEL = os.getenv("FORCE_CHANNEL")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

DB_FILE = "db.json"
IMAGE_LIMIT = 5

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

db = load_db()

def user_data(user):
    uid = str(user.id)
    if uid not in db:
        db[uid] = {
            "verified": False,
            "history": [],
            "images_today": 0,
            "last_image_day": str(datetime.utcnow().date())
        }
        save_db(db)
    return db[uid]

def reset_daily_limits(u):
    today = str(datetime.utcnow().date())
    if u["last_image_day"] != today:
        u["images_today"] = 0
        u["last_image_day"] = today

def is_member(user_id):
    try:
        m = bot.get_chat_member(FORCE_CHANNEL, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

def join_required(msg):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ عضو شدم", callback_data="check_join"))
    bot.send_message(
        msg.chat.id,
        "❌ برای استفاده از ربات باید:\n"
        "1️⃣ عضو کانال شوید\n"
        "2️⃣ به آخرین پست ریکشن بزنید\n\n"
        "سپس روی «عضو شدم» بزنید ✅",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_join(call):
    u = user_data(call.from_user)
    if is_member(call.from_user.id):
        u["verified"] = True
        save_db(db)
        bot.answer_callback_query(call.id, "✅ تایید شد")
        bot.send_message(call.message.chat.id, "✅ حالا می‌تونی پیام بفرستی")
    else:
        bot.answer_callback_query(call.id, "❌ هنوز عضو نیستی", show_alert=True)

def chat_ai(messages):
    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4.1-mini",
                "messages": messages
            },
            timeout=60
        ).json()
        return r["choices"][0]["message"]["content"]
    except:
        return "❌ خطا از سمت سرور هوش مصنوعی"

def image_ai(prompt):
    try:
        r = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-image-1",
                "prompt": prompt,
                "size": "1024x1024"
            },
            timeout=60
        ).json()
        return r["data"][0]["url"]
    except:
        return None

@bot.message_handler(commands=["reset"])
def reset_user(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    try:
        uid = msg.text.split()[1]
        if uid in db:
            db[uid]["verified"] = False
            save_db(db)
            bot.reply_to(msg, "✅ ریست شد")
    except:
        bot.reply_to(msg, "❌ فرمت: /reset USER_ID")

@bot.message_handler(content_types=["text"])
def handle_text(msg):
    u = user_data(msg.from_user)

    if FORCE_CHANNEL and not u["verified"]:
        join_required(msg)
        return

    reset_daily_limits(u)

    if msg.text.startswith("/img "):
        if u["images_today"] >= IMAGE_LIMIT:
            bot.reply_to(msg, "❌ محدودیت روزانه تصویر تمام شد")
            return
        img = image_ai(msg.text[5:])
        if not img:
            bot.reply_to(msg, "❌ خطا در تولید تصویر")
            return
        u["images_today"] += 1
        save_db(db)
        bot.send_photo(msg.chat.id, img)
        return

    u["history"].append({"role": "user", "content": msg.text})
    u["history"] = u["history"][-10:]

    reply = chat_ai(u["history"])
    u["history"].append({"role": "assistant", "content": reply})
    save_db(db)

    bot.reply_to(msg, reply)

@bot.message_handler(content_types=["voice"])
def handle_voice(msg):
    u = user_data(msg.from_user)

    if FORCE_CHANNEL and not u["verified"]:
        join_required(msg)
        return

    try:
        file_info = bot.get_file(msg.voice.file_id)
        file = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}").content

        r = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {API_KEY}"},
            files={"file": ("voice.ogg", file)},
            data={"model": "whisper-1"}
        ).json()

        text = r.get("text")
        if not text:
            bot.reply_to(msg, "❌ خطا در تبدیل ویس")
            return

        u["history"].append({"role": "user", "content": text})
        reply = chat_ai(u["history"])
        u["history"].append({"role": "assistant", "content": reply})
        save_db(db)

        bot.reply_to(msg, reply)
    except:
        bot.reply_to(msg, "❌ خطا در پردازش ویس")

# ✅ FIX قطعی 409
bot.remove_webhook(drop_pending_updates=True)
time.sleep(2)
bot.infinity_polling(skip_pending=True)
