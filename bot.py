import telebot, requests, os, json, time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

BOT_TOKEN = os.getenv("BOT_TOKEN")
GAPGPT_API_KEY = os.getenv("GAPGPT_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
FORCE_CHANNEL = os.getenv("FORCE_CHANNEL")

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
DB_FILE = "db.json"

if not os.path.exists(DB_FILE):
    open(DB_FILE, "w", encoding="utf-8").write("{}")

def load_db():
    return json.load(open(DB_FILE, "r", encoding="utf-8"))

def save_db(d):
    json.dump(d, open(DB_FILE, "w", encoding="utf-8"), ensure_ascii=False)

def user_data(u):
    d = load_db()
    uid = str(u.id)
    today = time.strftime("%Y-%m-%d")
    if uid not in d:
        d[uid] = {"name": u.first_name, "verified": False, "images": 0, "date": today, "history": []}
    if d[uid]["date"] != today:
        d[uid]["images"] = 0
        d[uid]["date"] = today
    save_db(d)
    return d[uid]

def member_check(uid):
    try:
        return bot.get_chat_member(FORCE_CHANNEL, uid).status in ("member", "administrator", "creator")
    except:
        return False

def join_markup():
    k = InlineKeyboardMarkup()
    k.add(InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{FORCE_CHANNEL.replace('@','')}"))
    k.add(InlineKeyboardButton("✅ بررسی عضویت", callback_data="check"))
    return k

LOCK_TEXT = "🔒 ابتدا عضو کانال شو و سپس روی «بررسی عضویت» بزن"

def chat_ai(history):
    try:
        r = requests.post(
            "https://api.gapgpt.app/v1/chat/completions",
            headers={"Authorization": f"Bearer {GAPGPT_API_KEY}", "Content-Type": "application/json"},
            json={"model": "gpt-5.2", "messages": history[-10:]},
            timeout=120
        )
        j = r.json()
        if "choices" not in j:
            return "❌ خطا از سمت سرور هوش مصنوعی"
        return j["choices"][0]["message"]["content"]
    except:
        return "❌ خطای داخلی، دوباره تلاش کن"

def image_ai(prompt):
    try:
        r = requests.post(
            "https://api.gapgpt.app/v1/images/generations",
            headers={"Authorization": f"Bearer {GAPGPT_API_KEY}", "Content-Type": "application/json"},
            json={"model": "gpt-image-1", "prompt": prompt, "size": "1024x1024"},
            timeout=120
        )
        j = r.json()
        if "data" not in j:
            return None
        url = j["data"][0]["url"]
        img = requests.get(url).content
        name = f"img_{time.time()}.png"
        open(name, "wb").write(img)
        return name
    except:
        return None

def pdf_make(text):
    name = f"pdf_{time.time()}.pdf"
    c = canvas.Canvas(name, pagesize=A4)
    w, h = A4
    y = h - 40
    for l in text.split("\n"):
        if y < 40:
            c.showPage()
            y = h - 40
        c.drawString(40, y, l[:110])
        y -= 14
    c.save()
    return name

@bot.callback_query_handler(func=lambda c: c.data == "check")
def check_join(c):
    if member_check(c.from_user.id):
        d = load_db()
        d[str(c.from_user.id)]["verified"] = True
        save_db(d)
        bot.answer_callback_query(c.id, "✅ تایید شد")
        bot.send_message(c.message.chat.id, "✅ تایید شد، پیام بفرست")
    else:
        bot.answer_callback_query(c.id, "❌ عضو کانال نیستی", show_alert=True)

@bot.message_handler(commands=["start"])
def start(m):
    u = user_data(m.from_user)
    if not u["verified"]:
        bot.send_message(m.chat.id, LOCK_TEXT, reply_markup=join_markup())
        return
    bot.send_message(m.chat.id, "✅ ربات آماده است")

@bot.message_handler(commands=["reset"])
def reset_user(m):
    if m.from_user.id != ADMIN_ID:
        return
    try:
        uid = m.text.split()[1]
        d = load_db()
        d[uid]["verified"] = False
        save_db(d)
        bot.send_message(m.chat.id, "✅ ریست شد")
    except:
        bot.send_message(m.chat.id, "/reset USER_ID")

@bot.message_handler(content_types=["text"])
def text_handler(m):
    u = user_data(m.from_user)
    if not u["verified"]:
        bot.send_message(m.chat.id, LOCK_TEXT, reply_markup=join_markup())
        return
    d = load_db()

    if m.text.startswith("تصویر:"):
        if m.from_user.id != ADMIN_ID and u["images"] >= 5:
            bot.send_message(m.chat.id, "❌ سقف امروز پر شده")
            return
        img = image_ai(m.text.replace("تصویر:", "").strip())
        if not img:
            bot.send_message(m.chat.id, "❌ خطا در ساخت تصویر")
            return
        if m.from_user.id != ADMIN_ID:
            u["images"] += 1
            d[str(m.from_user.id)] = u
            save_db(d)
        bot.send_photo(m.chat.id, open(img, "rb"))
        os.remove(img)
        return

    if m.text.startswith("پی دی اف:"):
        pdf = pdf_make(m.text.replace("پی دی اف:", "").strip())
        bot.send_document(m.chat.id, open(pdf, "rb"))
        os.remove(pdf)
        return

    u["history"].append({"role": "user", "content": m.text})
    ans = chat_ai(u["history"])
    u["history"].append({"role": "assistant", "content": ans})
    d[str(m.from_user.id)] = u
    save_db(d)
    bot.send_message(m.chat.id, ans)

@bot.message_handler(content_types=["voice"])
def voice_handler(m):
    u = user_data(m.from_user)
    if not u["verified"]:
        bot.send_message(m.chat.id, LOCK_TEXT, reply_markup=join_markup())
        return
    d = load_db()
    f = bot.get_file(m.voice.file_id)
    v = bot.download_file(f.file_path)
    name = f"voice_{time.time()}.ogg"
    open(name, "wb").write(v)

    try:
        r = requests.post(
            "https://api.gapgpt.app/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {GAPGPT_API_KEY}"},
            files={"file": open(name, "rb")},
            data={"model": "whisper-1"}
        )
        text = r.json().get("text")
    except:
        text = None

    os.remove(name)

    if not text:
        bot.send_message(m.chat.id, "❌ خطا در تبدیل ویس")
        return

    u["history"].append({"role": "user", "content": text})
    ans = chat_ai(u["history"])
    u["history"].append({"role": "assistant", "content": ans})
    d[str(m.from_user.id)] = u
    save_db(d)
    bot.send_message(m.chat.id, ans)

bot.infinity_polling(skip_pending=True)
