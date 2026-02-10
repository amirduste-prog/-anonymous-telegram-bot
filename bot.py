import os
import telebot
from telebot.types import Message

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

message_map = {}


@bot.message_handler(commands=['start', 'help'])
def start_help(message: Message):
    bot.send_message(
        message.chat.id,
        "👋 سلام!\n\n"
        "📨 پیام خودت رو بنویس و ارسال کن.\n"
        "پیامت به‌صورت ناشناس به ادمین می‌رسه."
    )


@bot.message_handler(
    func=lambda m: m.chat.id != ADMIN_ID and not m.text.startswith('/'),
    content_types=['text']
)
def handle_user_message(message: Message):
    user = message.from_user
    username = f"@{user.username}" if user.username else "ندارد"

    admin_text = (
        "📩 <b>پیام جدید ناشناس</b>\n\n"
        f"👤 <b>Name:</b> {user.first_name}\n"
        f"🔗 <b>Username:</b> {username}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n\n"
        f"💬 <b>Message:</b>\n{message.text}"
    )

    sent = bot.send_message(ADMIN_ID, admin_text)
    message_map[sent.message_id] = user.id

    bot.send_message(message.chat.id, "✅ پیام شما ارسال شد")


@bot.message_handler(
    func=lambda m: m.chat.id == ADMIN_ID,
    content_types=['text']
)
def handle_admin_reply(message: Message):
    if not message.reply_to_message:
        return

    replied_id = message.reply_to_message.message_id

    if replied_id not in message_map:
        bot.send_message(ADMIN_ID, "❌ این پیام متصل نیست.")
        return

    target_user_id = message_map[replied_id]
    bot.send_message(target_user_id, message.text)


print("✅ Bot is running...")
bot.infinity_polling(skip_pending=True)
