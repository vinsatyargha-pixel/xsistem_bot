import telebot
import random
import string
from telebot import types

TOKEN = "8087735462:AAGII-XvO3hJy3YgDd3b0vjiIHjnQCn4Ej4"
bot = telebot.TeleBot(TOKEN)

def buat_password():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(10))

# ========== HANDLE TEXT COMMAND ==========
@bot.message_handler(func=lambda m: m.text and any(
    cmd in m.text.lower() for cmd in ['/reset', '/repass', '/repas']
))
def handle_reset(message):
    """Hanya handle text command /reset"""
    try:
        # Parse: /reset userid asset
        text = message.text.strip()
        parts = text.split()
        
        if len(parts) < 3:
            bot.reply_to(message, "Format: /reset UserID Asset")
            return
        
        user_id = parts[1]
        asset = parts[2]
        
        print(f"📩 Reset: {user_id} {asset} dari @{message.from_user.username}")
        
        # Buat tombol di grup
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Reset", callback_data=f"ok_{message.from_user.id}_{user_id}_{asset}"),
            types.InlineKeyboardButton("❌ Tolak", callback_data=f"no_{message.from_user.id}")
        )
        
        # Reply dengan tombol
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

# ========== IGNORE PHOTO CAPTION ==========
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """IGNORE semua foto dan captionnya!"""
    # ⚠️ JANGAN APA-APA! Biarin aja fotonya
    # Jangan process /reset dari caption foto!
    pass

# ========== CALLBACK HANDLER ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Handle pilihan Captain"""
    try:
        if call.data.startswith('ok_'):
            # Format: ok_CS_ID_USER_ID_ASSET
            _, cs_id, user_id, asset = call.data.split('_')
            cs_id = int(cs_id)
            
            password = buat_password()
            
            # Format: user_ID - Asset
            # Password baru :
            message_text = f"{user_id} - {asset}\nPassword baru : {password}"
            
            # Kirim password di grup
            bot.send_message(
                call.message.chat.id,
                message_text,
                reply_to_message_id=call.message.reply_to_message.message_id
            )
            
            # Update pesan tombol
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
            
            # Kirim notifikasi penolakan
            bot.send_message(
                call.message.chat.id,
                "❌ Permintaan ditolak Captain !!",
                reply_to_message_id=call.message.reply_to_message.message_id
            )
            
            # Update pesan tombol
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

if __name__ == "__main__":
    print("🤖 Bot started - Ignoring photo captions!")
    bot.polling(none_stop=True)
