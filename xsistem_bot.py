import telebot
import random
import string

# ===== CONFIG (TEST ONLY) =====
TOKEN = "8087735462:AAGduMGrAaut2mlPanwlsCq7K-82fqIFuOo"
ADMIN_CHAT_ID = 5720343562
bot = telebot.TeleBot(TOKEN)

TRIGGERS = ("reset", "repas", "repass")

# ===== PASSWORD GENERATOR =====
def generate_password(length=9):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# ===== UNIVERSAL HANDLER (TEXT + FOTO) =====
@bot.message_handler(content_types=["text", "photo"])
def universal_handler(message):
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
            "❌ Format salah!\n\nGunakan:\nreset USER_ID\n\nContoh:\nreset TEST123"
        )
        return

    user_asset = parts[1]
    password = generate_password()

    response = (
        "✅ PASSWORD READY!\n"
        f"USER ID : {user_asset}\n\n"
        f"🔐 Password: `{password}`\n\n"
        "⚠️ Berikan ke user segera!"
    )

    bot.reply_to(message, response, parse_mode="Markdown")

# ===== START BOT =====
if __name__ == "__main__":
    print("🚀 Bot TEST running...")
    bot.polling(none_stop=True, timeout=60)
