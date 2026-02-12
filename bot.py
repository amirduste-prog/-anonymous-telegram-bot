import telebot
import requests
import os
import json
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

BOT_TOKEN = os.getenv("BOT_TOKEN")
GAPGPT_API_KEY = os.getenv("GAPGPT_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
FORCE_CHANNEL = os.getenv("FORCE_CHANNEL")

bot = telebot.TeleBot(BOT_TOKEN)

if not os.path.exists("db.json"):
    with open("db.json","w",encoding="utf-8") as f:
        json.dump({},f)

def load_db():
    with open("db.json","r",encoding="utf-8") as f:
        return json.load(f)

def save_db(d):
    with open("db.json","w",encoding="utf-8") as f:
        json.dump(d,f,ensure_ascii=False)

def user_data(u):
    d = load_db()
    uid = str(u.id)
    today = time.strftime("%Y-%m-%d")
    if uid not in d:
        d[uid] = {"name":u.first_name,"images":0,"date":today,"history":[]}
    if d[uid]["date"] != today:
        d[uid]["images"] = 0
        d[uid]["date"] = today
    save_db(d)
    return d[uid]

def member_check(uid):
    try:
        s = bot.get_chat_member(FORCE_CHANNEL,uid).status
        return s in ["member","administrator","creator"]
    except:
        return False

def join_markup():
    k = InlineKeyboardMarkup()
    k.add(InlineKeyboardButton("عضویت در کانال",url=f"https://t.me/{FORCE_CHANNEL.replace('@','')}"))
    k.add(InlineKeyboardButton("بررسی عضویت",callback_data="check"))
    return k

def chat_ai(history):
    r = requests.post(
        "https://api.gapgpt.app/v1/chat/completions",
        headers={
            "Authorization":f"Bearer {GAPGPT_API_KEY}",
            "Content-Type":"application/json"
        },
        json={
            "model":"gpt-5.2",
            "messages":history[-10:]
        },
        timeout=120
    )
    return r.json()["choices"][0]["message"]["content"]

def image_ai(prompt):
    r = requests.post(
        "https://api.gapgpt.app/v1/images/generations",
        headers={
            "Authorization":f"Bearer {GAPGPT_API_KEY}",
            "Content-Type":"application/json"
        },
        json={
            "model":"gpt-image-1",
            "prompt":prompt,
            "size":"1024x1024"
        }
    )
    url = r.json()["data"][0]["url"]
    img = requests.get(url).content
    name = f"img_{time.time()}.png"
    open(name,"wb").write(img)
    return name

def pdf_make(text):
    name = f"pdf_{time.time()}.pdf"
    c = canvas.Canvas(name,pagesize=A4)
    w,h = A4
    y = h-40
    for l in text.split("\n"):
        if y < 40:
            c.showPage()
            y = h-40
        c.drawString(40,y,l[:110])
        y -= 14
    c.save()
    return name

@bot.callback_query_handler(func=lambda c: c.data=="check")
def check_join(c):
    if member_check(c.from_user.id):
        bot.answer_callback_query(c.id,"✅ تایید شد")
        bot.send_message(c.message.chat.id,"می‌تونی از ربات استفاده کنی")
    else:
        bot.answer_callback_query(c.id,"❌ هنوز عضو نیستی",show_alert=True)

@bot.message_handler(commands=["start"])
def start(m):
    user_data(m.from_user)
    if not member_check(m.from_user.id):
        bot.send_message(m.chat.id,"برای استفاده عضو کانال شو",reply_markup=join_markup())
        return
    bot.send_message(m.chat.id,"ربات آماده است")

@bot.message_handler(content_types=["text"])
def text(m):
    if not member_check(m.from_user.id):
        bot.send_message(m.chat.id,"اول عضو کانال شو",reply_markup=join_markup())
        return
    u = user_data(m.from_user)
    if m.from_user.id == ADMIN_ID and m.text.lower() == "member":
        d = load_db()
        bot.send_message(m.chat.id,"\n".join([f'{d[i]["name"]} | {i}' for i in d]))
        return
    if m.text.startswith("تصویر:"):
        if m.from_user.id != ADMIN_ID and u["images"] >= 5:
            bot.send_message(m.chat.id,"سقف امروز پر شده")
            return
        img = image_ai(m.text.replace("تصویر:",""))
        if m.from_user.id != ADMIN_ID:
            d = load_db()
            d[str(m.from_user.id)]["images"] += 1
            save_db(d)
        bot.send_photo(m.chat.id,open(img,"rb"))
        os.remove(img)
        return
    if m.text.startswith("پی دی اف:"):
        pdf = pdf_make(m.text.replace("پی دی اف:",""))
        bot.send_document(m.chat.id,open(pdf,"rb"))
        os.remove(pdf)
        return
    u["history"].append({"role":"user","content":m.text})
    ans = chat_ai(u["history"])
    u["history"].append({"role":"assistant","content":ans})
    d = load_db()
    d[str(m.from_user.id)] = u
    save_db(d)
    bot.send_message(m.chat.id,ans)

@bot.message_handler(content_types=["voice"])
def voice(m):
    if not member_check(m.from_user.id):
        bot.send_message(m.chat.id,"اول عضو کانال شو",reply_markup=join_markup())
        return
    f = bot.get_file(m.voice.file_id)
    v = bot.download_file(f.file_path)
    name = f"voice_{time.time()}.ogg"
    open(name,"wb").write(v)
    r = requests.post(
        "https://api.gapgpt.app/v1/audio/transcriptions",
        headers={"Authorization":f"Bearer {GAPGPT_API_KEY}"},
        files={"file":open(name,"rb")},
        data={"model":"whisper-1"}
    )
    text = r.json()["text"]
    os.remove(name)
    u = user_data(m.from_user)
    u["history"].append({"role":"user","content":text})
    ans = chat_ai(u["history"])
    u["history"].append({"role":"assistant","content":ans})
    d = load_db()
    d[str(m.from_user.id)] = u
    save_db(d)
    bot.send_message(m.chat.id,ans)

bot.infinity_polling()
