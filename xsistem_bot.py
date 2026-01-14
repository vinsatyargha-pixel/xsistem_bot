import telebot
import random
import string
import time
from telebot import types
import logging

# ========== CONFIG ==========
TOKEN = "8087735462:AAGII-XvO3hJy3YgDd3b0vjiIHjnQCn4Ej4"  # PASTIKAN TOKEN BENAR!
CAPTAIN_GROUP_ID = -5720343562  # GANTI INI!

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN)

# ========== FUNGSI GENERATE PASSWORD ==========
def generate_password():
    upper = random.choice(string.ascii_uppercase)
    lower = random.choice(string.ascii_lowercase)
    numbers = ''.join(random.choice(string.digits) for _ in range(8))
    password_chars = list(upper + lower + numbers)
    random.shuffle(password_chars)
    return ''.join(password_chars)

# ========== TRIGGER RESET ==========
@bot.message_handler(func=lambda m: any(cmd in m.text.lower() for cmd in ['/reset', '/repass', '/repas']))
def handle_reset(message):
    try:
        text = message.text.strip()
        parts = text.split()
        
        if len(parts) < 3:
            bot.reply_to(message, "Format: /reset UserID Asset\nContoh: /reset Appank07 G200M")
            return
        
        # Ambil user_id dan asset (bisa dari berbagai format)
        user_id = parts[1]
        asset = parts[2]
        
        # Hapus tanda "-" jika ada
        user_id = user_id.replace('-', '').strip()
        asset = asset.replace('-', '').strip()
        
        logger.info(f"Reset request from {message.from_user.id}: {user_id} {asset}")
        
        # Kirim ke group captain
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Reset", callback_data=f"approve_{message.from_user.id}_{user_id}_{asset}"),
            types.InlineKeyboardButton("❌ Tolak", callback_data=f"reject_{message.from_user.id}")
        )
        
        bot.send_message(
            CAPTAIN_GROUP_ID,
            f"🔔 *RESET REQUEST*\n\n"
            f"CS: {message.from_user.full_name} (@{message.from_user.username})\n"
            f"UserID: `{user_id}`\n"
            f"Asset: `{asset}`\n\n"
            f"Pilih:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
        bot.reply_to(message, "✅ Request dikirim ke Captain!")
        
    except Exception as e:
        logger.error(f"Error in handle_reset: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)}")

# ========== HANDLE PHOTO ==========
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        bot.forward_message(CAPTAIN_GROUP_ID, message.chat.id, message.message_id)
        bot.reply_to(message, "📸 Bukti diteruskan!")
    except Exception as e:
        logger.error(f"Error forwarding photo: {e}")

# ========== CAPTAIN APPROVAL ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))
def approve(call):
    try:
        data = call.data.split('_')
        cs_id = int(data[1])
        user_id = data[2]
        asset = data[3]
        
        new_password = generate_password()
        
        # Format: user_ID - Asset
        # Password baru :
        message_text = f"{user_id} - {asset}\nPassword baru : {new_password}"
        
        # Kirim ke CS
        bot.send_message(cs_id, message_text)
        
        # Update pesan
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"✅ APPROVED\n{user_id} - {asset}\nPassword: {new_password}"
        )
        
        bot.answer_callback_query(call.id, "✅ Password dikirim")
        
    except Exception as e:
        logger.error(f"Error in approve: {e}")
        bot.answer_callback_query(call.id, "❌ Error")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_'))
def reject(call):
    try:
        cs_id = int(call.data.split('_')[1])
        
        # Kirim ke CS
        bot.send_message(cs_id, "Permintaan anda ditolak Captain !!")
        
        # Update pesan
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"❌ REJECTED\nDitolak oleh Captain"
        )
        
        bot.answer_callback_query(call.id, "❌ Request ditolak")
        
    except Exception as e:
        logger.error(f"Error in reject: {e}")
        bot.answer_callback_query(call.id, "❌ Error")

# ========== START ==========
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        "🤖 *Simple Reset Bot*\n\n"
        "Kirim: `/reset UserID Asset`\n"
        "Contoh: `/reset Appank07 G200M`\n\n"
        "Request akan ke Captain untuk approval.",
        parse_mode='Markdown'
    )

# ========== MAIN ==========
if __name__ == "__main__":
    logger.info("🚀 Starting Simple Reset Bot...")
    logger.info(f"Captain Group ID: {CAPTAIN_GROUP_ID}")
    
    try:
        # Cek bot info dulu
        me = bot.get_me()
        logger.info(f"Bot: @{me.username} ({me.id})")
        
        # Polling dengan parameter aman
        bot.polling(
            none_stop=True,
            interval=1,
            timeout=30,
            allowed_updates=["message", "callback_query"]
        )
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        time.sleep(5)

