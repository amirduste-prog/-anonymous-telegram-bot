import telebot
import os, json, datetime
from telebot import types
from openai import OpenAI
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader

# ================= CONFIG =================
BOT_TOKEN = "TELEGRAM_BOT_TOKEN"
ADMIN_ID = 123456789
CHANNEL_USERNAME = "@your_channel"

GAPGPT_API_KEY = "YOUR_GAPGPT_API_KEY"
GAPGPT_BASE_URL = "https://api.gapgpt.app/v1"

# ================= BOT ====================
bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(
    base_url=GAPGPT_BASE_URL,
    api_key=GAPGPT_API_KEY
)

# ================= FILES ==================
USERS_FILE = "users.json"
MEMORY_FILE = "memory.json"
LIMIT_FILE = "daily_limit.json"

# ================= UTILS ==================
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

def is_member(user_id):
    try:
        s = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return s in ["member", "administrator", "creator"]
    except:
        return False

# ================= MEMORY =================
def add_memory(uid, role, text):
    uid = str(uid)
    memory.setdefault(uid, [])
    memory[uid].append({"role": role, "content": text})
    memory[uid] = memory[uid][-10:]
    save(MEMORY_FILE, memory)

# ================= AI CHAT ================
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

# ================= IMAGE LIMIT ============
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

# ================= START ==================
@bot.message_handler(commands=["start"])
def start(m):
    users[str(m.from_user.id)] = {
        "name": m.from_user.first_name
    }
    save(USERS_FILE, users)
    bot.reply_to(m, "✅ ربات فعال شد")

# ================= CHAT ===================
@bot.message_handler(content_types=["text"])
def chat(m):
    if not is_member(m.from_user.id):
        bot.reply_to(m, "❌ ابتدا عضو کانال شوید")
        return

    if m.text == "member" and m.from_user.id == ADMIN_ID:
        txt = f"👥 تعداد اعضا: {len(users)}\n\n"
        for uid, u in users.items():
            txt += f"{u['name']} | {uid}\n"
        bot.send_message(m.chat.id, txt)
        return

    if m.text.startswith("/image"):
        if not can_image(m.from_user.id):
            bot.reply_to(m, "⛔ محدودیت ۵ تصویر در روز")
            return

        prompt = m.text.replace("/image", "")
        img = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )
        bot.send_photo(m.chat.id, img.data[0].url)
        return

    if m.text.startswith("/pdf"):
        text = m.text.replace("/pdf", "")
        filename = f"{m.from_user.id}.pdf"
        c = canvas.Canvas(filename)
        c.drawString(50, 800, text)
        c.save()
        bot.send_document(m.chat.id, open(filename, "rb"))
        return

    reply = ai_chat(m.from_user.id, m.text)
    bot.reply_to(m, reply)

# ================= PDF READ ===============
@bot.message_handler(content_types=["document"])
def read_pdf(m):
    file = bot.download_file(
        bot.get_file(m.document.file_id).file_path
    )
    with open("file.pdf", "wb") as f:
        f.write(file)

    reader = PdfReader("file.pdf")
    text = "\n".join(p.extract_text() for p in reader.pages)
    answer = ai_chat(m.from_user.id, text)
    bot.reply_to(m, answer)

# ================= RUN ====================
bot.infinity_polling()
