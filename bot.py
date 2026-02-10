import os
import telebot

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# نگاشت پیام ادمین به user_id
message_map = {}

# =========================
# /start و /help (امن)
# =========================
@bot.message_handler(commands=["start", "help"])
def start_help(message):
    bot.send_message(
        message.chat.id,
        "👋 سلام\n"
        "پیامت رو بنویس، به‌صورت ناشناس به ادمین ارسال می‌شه."
    )
    # ⛔ هیچ اطلاعاتی برای ادمین ارسال نمی‌شود

# =========================
# پیام کاربران (غیر ادمین)
# =========================
@bot.message_handler(func=lambda m: m.chat.id != ADMIN_ID and m.text and m.text.strip())
def handle_user_message(message):
    user = message.from_user

    admin_message = (
        "📩 <b>پیام ناشناس جدید</b>\n\n"
        f"👤 نام: {user.first_name}\n"
        f"🔗 یوزرنیم: @{user.username if user.username else 'ندارد'}\n"
        f"🆔 آیدی عددی: <code>{user.id}</code>\n\n"
        "💬 متن پیام:\n"
        f"{message.text}"
    )

    sent = bot.send_message(ADMIN_ID, admin_message)

    # ذخیره ارتباط پیام برای Reply
    message_map[sent.message_id] = user.id

    # پیام تأیید برای کاربر
    bot.send_message(message.chat.id, "✅ ارسال شد")

# =========================
# پاسخ ادمین با Reply
# =========================
@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID and m.reply_to_message)
def handle_admin_reply(message):
    replied_id = message.reply_to_message.message_id

    if replied_id not in message_map:
        bot.send_message(ADMIN_ID, "❌ این پیام به کاربری متصل نیست.")
        return

    user_id = message_map[replied_id]

    bot.send_message(user_id, message.text)

# =========================
# Run
# =========================
print("✅ Bot is running...")
bot.infinity_polling()
