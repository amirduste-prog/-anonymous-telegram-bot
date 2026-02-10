import telebot
from telebot.types import Message

# ================== CONFIG ==================
BOT_TOKEN = "8290432435:AAGK72Hy672je-kt_2SRN6LAlwY_76lN_IU"
ADMIN_ID = 7242791584  # آیدی عددی خودت
# ============================================

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# admin_message_id -> user_id
message_map = {}


# ---------- START & HELP ----------
@bot.message_handler(commands=['start', 'help'])
def start_help(message: Message):
    bot.send_message(
        message.chat.id,
        "👋 سلام!\n\n"
        "📨 پیام خودت رو بنویس و ارسال کن.\n"
        "پیامت به‌صورت ناشناس به ادمین می‌رسه."
    )


# ---------- USER MESSAGE ----------
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

    # ذخیره ارتباط پیام ادمین با کاربر
    message_map[sent.message_id] = user.id

    # تایید ارسال برای کاربر
    bot.send_message(message.chat.id, "✅ پیام شما ارسال شد")


# ---------- ADMIN REPLY ----------
@bot.message_handler(
    func=lambda m: m.chat.id == ADMIN_ID,
    content_types=['text']
)
def handle_admin_reply(message: Message):
    if not message.reply_to_message:
        return

    replied_id = message.reply_to_message.message_id

    if replied_id not in message_map:
        bot.send_message(
            ADMIN_ID,
            "❌ این پیام به هیچ کاربری متصل نیست."
        )
        return

    target_user_id = message_map[replied_id]

    try:
        bot.send_message(target_user_id, message.text)
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ خطا:\n{e}")


print("✅ Bot is running...")
bot.infinity_polling(skip_pending=True)
