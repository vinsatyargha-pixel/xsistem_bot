import telebot
from telebot import types
import random
import string

# ===== CONFIG (TEST ONLY) =====
TOKEN = "8087735462:AAGduMGrAaut2mlPanwlsCq7K-82fqIFuOo"
CAPTAIN_USERNAME = "@vingeance"   # yang di-tag
bot = telebot.TeleBot(TOKEN)

TRIGGERS = ("reset", "repas", "repass")

# ===== PASSWORD GENERATOR =====
def generate_password(length=9):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# ===== HANDLE TEXT + PHOTO =====
@bot.message_handler(content_types=["text", "photo"])
def handle_request(message):
    text = ""

    if message.text:
        text = message.text
    elif message.caption:
        text = message.caption
    else:
        return

    text_lower = text.lower()
    if not any(t in text_lower for t in TRIGGERS):
        return

    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(
    message,
    "❌ Format salah!\n\n"
    "Gunakan:\n"
    "REPASS\n\n"
    "USER_ID - ASSET\n"
    "Nama Bank | Nama Rek | Nomor Rek\n"
    "Bank Tujuan DEPOSIT\n"
    "Wallet:\n"
    "Officer:\n"
)

        return

    user_asset = parts[1]

    # Inline button
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_ok = types.InlineKeyboardButton(
        "✅ Resetkan", callback_data=f"ok|{user_asset}"
    )
    btn_no = types.InlineKeyboardButton(
        "❌ Tolak", callback_data=f"no|{user_asset}"
    )
    markup.add(btn_ok, btn_no)

    response = (
        f"🔔 {CAPTAIN_USERNAME}\n\n"
        f"🧾 *Permintaan Reset Password*\n"
        f"USER ID : `{user_asset}`\n\n"
        "Silakan pilih tindakan:"
    )

    bot.reply_to(message, response, parse_mode="Markdown", reply_markup=markup)

# ===== CALLBACK HANDLER =====
@bot.callback_query_handler(func=lambda call: call.data.startswith(("ok|", "no|")))
def handle_action(call):
    action, user_asset = call.data.split("|", 1)

    if action == "ok":
        password = generate_password()
        text = (
            "✅ PASSWORD READY!\n"
            f"USER ID : {user_asset}\n\n"
            f"🔐 Password: `{password}`\n\n"
            "⚠️ Berikan ke user segera!"
        )
    else:
        text = (
            "❌ REQUEST DITOLAK\n"
            f"USER ID : {user_asset}"
        )

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        parse_mode="Markdown"
    )

    bot.answer_callback_query(call.id)

# ===== START BOT =====
if __name__ == "__main__":
    print("🚀 Bot running (approval mode)...")
    bot.polling(none_stop=True, timeout=60)

