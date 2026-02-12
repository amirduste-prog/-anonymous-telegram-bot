import os
import json
import datetime
import telebot
from telebot import types
from openai import OpenAI
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader

# ================= ENV =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GAPGPT_API_KEY = os.getenv("GAPGPT_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

GAPGPT_BASE_URL = "https://api.gapgpt.app/v1"

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN is invalid or not set")

# ================= BOT =================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
client = OpenAI(
    base_url=GAPGPT_BASE_URL,
    api_key=GAPGPT_API_KEY
)

# ================= FILES ===============
USERS_FILE = "users.json"
MEMORY_FILE = "memory.json"
LIMIT_FILE = "daily_limit.json"

# ================= UTILS ===============
def load(file, default):
    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as f:
            json.dump(default, f)
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

users = load(USERS_FILE, {})
memory = load(MEMORY_FILE, {})
limits = load(LIMIT_FILE, {})

def today():
    return str(datetime.date.today())

# ================= CHANNEL CHECK =======
def is_member(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ["member", "administrator", "creator"]
    except:
        return False

# ================= JOIN KEYBOARD =======
def join_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)

    join_btn = types.InlineKeyboardButton(
        "📢 عضویت در کانال",
        url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"
    )

    check_btn = types.InlineKeyboardButton(
        "✅ بررسی عضویت",
        callback_data="check_join"
    )

    kb.add(join_btn, check_btn)
    return kb

# ================= MEMORY ==============
def add_memory(uid, role, text):
    uid = str(uid)
    memory.setdefault(uid, [])
    memory[uid].append({"role": role, "content": text})
    memory[uid] = memory[uid][-10:]
    save(MEMORY_FILE, memory)

# ================= AI CHAT =============
def ai_chat(user_id, text):
    uid = str(user_id)
    msgs = memory.get(uid, [])
    msgs.append({"role": "user", "content": text})

    res = client.chat.completions.create(
        model="gpt-4o",
        messages=msgs
    )

    answer = res.choices[0].message.content
    add_memory(user_id, "user", text)
    add_memory(user_id, "assistant", answer)
    return answer

# ================= IMAGE LIMIT =========
def can_image(user_id):
    if user_id == ADMIN_ID:
        return True

    uid = str(user_id)
    limits.setdefault(uid, {})
    limits[uid].setdefault(today(), 0)

    if limits[uid][today()] >= 5:
        return False

    limits[uid][today()] += 1
    save(LIMIT_FILE, limits)
    return True

# ================= START ===============
@bot.message_handler(commands=["start"])
def start(m):
    users[str(m.from_user.id)] = {
        "name": m.from_user.first_name
    }
    save(USERS_FILE, users)

    if not is_member(m.from_user.id):
        bot.send_message(
            m.chat.id,
            "⚠️ برای استفاده از ربات ابتدا عضو کانال شوید:",
            reply_markup=join_keyboard()
        )
        return

    bot.reply_to(m, "✅ ربات فعال شد، خوش اومدی!")

# ================= CALLBACK ============
@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join(call):
    if is_member(call.from_user.id):
        bot.edit_message_text(
            "✅ عضویت شما تایید شد\nحالا می‌تونی از ربات استفاده کنی",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        bot.answer_callback_query(
            call.id,
            "❌ هنوز عضو کانال نیستی",
            show_alert=True
        )

# ================= CHAT ================
@bot.message_handler(content_types=["text"])
def chat(m):
    if not is_member(m.from_user.id):
        bot.send_message(
            m.chat.id,
            "⛔ برای استفاده از ربات باید عضو کانال باشی:",
            reply_markup=join_keyboard()
        )
        return

    # ---- ADMIN ----
    if m.text == "member" and m.from_user.id == ADMIN_ID:
        txt = f"👥 تعداد اعضا: {len(users)}\n\n"
        for uid, u in users.items():
            txt += f"{u['name']} | {uid}\n"
        bot.send_message(m.chat.id, txt)
        return

    # ---- IMAGE ----
    if m.text.startswith("/image"):
        if not can_image(m.from_user.id):
            bot.reply_to(m, "⛔ محدودیت ۵ تصویر در روز")
            return

        prompt = m.text.replace("/image", "").strip()
        img = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )
        bot.send_photo(m.chat.id, img.data[0].url)
        return

    # ---- PDF CREATE ----
    if m.text.startswith("/pdf"):
        text = m.text.replace("/pdf", "").strip()
        filename = f"{m.from_user.id}.pdf"

        c = canvas.Canvas(filename)
        c.drawString(40, 800, text)
        c.save()

        bot.send_document(m.chat.id, open(filename, "rb"))
        return

    # ---- NORMAL CHAT ----
    reply = ai_chat(m.from_user.id, m.text)
    bot.reply_to(m, reply)

# ================= PDF READ ============
@bot.message_handler(content_types=["document"])
def read_pdf(m):
    if not is_member(m.from_user.id):
        bot.send_message(
            m.chat.id,
            "⚠️ ابتدا عضو کانال شوید:",
            reply_markup=join_keyboard()
        )
        return

    file_info = bot.get_file(m.document.file_id)
    file_bytes = bot.download_file(file_info.file_path)

    with open("input.pdf", "wb") as f:
        f.write(file_bytes)

    reader = PdfReader("input.pdf")
    text = "\n".join(p.extract_text() or "" for p in reader.pages)

    answer = ai_chat(m.from_user.id, text)
    bot.reply_to(m, answer)

# ================= RUN =================
print("✅ Bot is running...")
bot.infinity_polling()
