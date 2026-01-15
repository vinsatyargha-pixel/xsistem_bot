import telebot
import random
import string
from telebot import types

TOKEN = "8087735462:AAGII-XvO3hJy3YgDd3b0vjiIHjnQCn4Ej4"
# CAPTAIN_GROUP_ID = -1001234567890  # ID GRUP RESET PASSWORD

bot = telebot.TeleBot(TOKEN)

def buat_password():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(10))

# ========== HANDLER DI GRUP ==========
@bot.message_handler(func=lambda m: m.text and any(
    cmd in m.text.lower() for cmd in ['/reset', '/repass', '/repas']
))
def handle_reset_grup(message):
    """Handle reset command DI GRUP"""
    try:
        # Parse message
        text = message.text.strip()
        parts = text.split()
        
        if len(parts) < 3:
            bot.reply_to(message, "Format: /reset UserID Asset")
            return
        
        user_id = parts[1]
        asset = parts[2]
        
        print(f"📩 Reset di grup: {user_id} {asset} dari @{message.from_user.username}")
        
        # Buat tombol Reset/Tolak DI GRUP
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Reset", callback_data=f"ok_{message.from_user.id}_{user_id}_{asset}"),
            types.InlineKeyboardButton("❌ Tolak", callback_data=f"no_{message.from_user.id}")
        )
        
        # Reply di grup dengan tombol
        bot.reply_to(
            message,
            f"🔔 *RESET REQUEST*\n\n"
            f"👤 CS: {message.from_user.full_name}\n"
            f"🆔 User: `{user_id}`\n"
            f"🎮 Asset: `{asset}`\n\n"
            f"**PILIH:**",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        print(f"❌ Error: {e}")
        bot.reply_to(message, "❌ Error!")

# ========== PHOTO DI GRUP ==========
@bot.message_handler(content_types=['photo'])
def handle_photo_grup(message):
    """Foto di grup cuma forward ke reply atau ignore"""
    # Biarin aja, nggak perlu di-handle khusus
    pass

# ========== CALLBACK HANDLER ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_grup(call):
    """Handle pilihan Reset/Tolak DI GRUP"""
    try:
        if call.data.startswith('ok_'):
            # Format: ok_CS_ID_USER_ID_ASSET
            _, cs_id, user_id, asset = call.data.split('_')
            cs_id = int(cs_id)
            
            password = buat_password()
            
            # FORMAT YANG DIMINTA:
            # user_ID - Asset
            # Password baru :
            message_text = f"{user_id} - {asset}\nPassword baru : {password}"
            
            # Kirim password DI GRUP (reply ke message asli)
            bot.send_message(
                call.message.chat.id,
                message_text,
                reply_to_message_id=call.message.reply_to_message.message_id
            )
            
            # Update tombol jadi approved
            bot.edit_message_text(
                f"✅ *RESET DISETUJUI*\n\n"
                f"User: `{user_id}`\n"
                f"Asset: `{asset}`\n"
                f"Password: `{password}`",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
            
            bot.answer_callback_query(call.id, "✅ Password dikirim")
            
        elif call.data.startswith('no_'):
            cs_id = int(call.data.split('_')[1])
            
            # Kirim notifikasi penolakan DI GRUP
            bot.send_message(
                call.message.chat.id,
                "❌ Permintaan ditolak Captain !!",
                reply_to_message_id=call.message.reply_to_message.message_id
            )
            
            # Update tombol jadi rejected
            bot.edit_message_text(
                f"❌ *REQUEST DITOLAK*",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
            
            bot.answer_callback_query(call.id, "❌ Ditolak")
            
    except Exception as e:
        print(f"❌ Callback error: {e}")
        bot.answer_callback_query(call.id, "❌ Error")

# ========== START ==========
@bot.message_handler(commands=['start', 'help'])
def start(message):
    if message.chat.type in ['group', 'supergroup']:
        bot.reply_to(message,
            "🤖 *Reset Password Bot*\n\n"
            "CS kirim: `/reset UserID Asset`\n"
            "Contoh: `/reset kitty95 g20`\n\n"
            "Captain pilih: Reset atau Tolak",
            parse_mode='Markdown'
        )

if __name__ == "__main__":
    print("🤖 Bot for GROUP started!")
    bot.polling(none_stop=True)
