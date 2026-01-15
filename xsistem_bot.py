import telebot
import random
import string
from telebot import types
import time

# ========== CONFIG ==========
TOKEN = "8087735462:AAGII-XvO3hJy3YgDd3b0vjiIHjnQCn4Ej4"
CAPTAIN_ID = 5720343562  # ID kamu

bot = telebot.TeleBot(TOKEN)

# ========== FUNGSI ==========
def buat_password():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(10))

# ========== RESET HANDLER ==========
@bot.message_handler(func=lambda m: m.text and any(
    cmd in m.text.lower() for cmd in ['/reset', '/repass', '/repas']
))
def handle_reset(m):
    try:
        # Parse message
        text = m.text.strip()
        parts = text.split()
        
        if len(parts) < 3:
            bot.reply_to(m, "❌ Format: `/reset UserID Asset`\nContoh: `/reset kitty95 g20`", parse_mode='Markdown')
            return
        
        user_id = parts[1]
        asset = parts[2]
        
        print(f"📩 Reset dari @{m.from_user.username}: {user_id} {asset}")
        
        # Simpan data CS untuk callback
        cs_data = {
            'id': m.from_user.id,
            'name': m.from_user.full_name,
            'username': m.from_user.username
        }
        
        # Buat tombol untuk Captain
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Reset", callback_data=f"ok_{m.from_user.id}_{user_id}_{asset}"),
            types.InlineKeyboardButton("❌ Tolak", callback_data=f"no_{m.from_user.id}")
        )
        
        # Kirim ke Captain
        bot.send_message(
            CAPTAIN_ID,
            f"🔔 *RESET REQUEST*\n\n"
            f"👤 **CS:** {cs_data['name']}\n"
            f"📱 **Username:** @{cs_data['username'] or 'N/A'}\n"
            f"🆔 **User:** `{user_id}`\n"
            f"🎮 **Asset:** `{asset}`\n\n"
            f"⏳ **Pilih aksi:**",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
        # ✅ KONFIRMASI KE CS (INI YANG BENAR!)
        bot.reply_to(m, "✅ *Request sudah dikirim ke Captain!*\nTunggu approval...", parse_mode='Markdown')
        
    except Exception as e:
        print(f"❌ Error: {e}")
        bot.reply_to(m, "❌ Error processing request")

# ========== PHOTO HANDLER ==========
@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    """HANYA FORWARD FOTO KE CAPTAIN, TANPA REPLY KE CS!"""
    try:
        # Hanya forward ke Captain, TIDAK REPLY KE CS
        bot.forward_message(CAPTAIN_ID, m.chat.id, m.message_id)
        print(f"📸 Foto diteruskan dari @{m.from_user.username}")
        # ⚠️ JANGAN REPLY APA-APA KE CS!
    except Exception as e:
        print(f"❌ Error forwarding photo: {e}")
        # Jangan reply error ke CS juga!

# ========== CALLBACK HANDLER ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        if call.data.startswith('ok_'):
            # Format: ok_CS_ID_USER_ID_ASSET
            _, cs_id, user_id, asset = call.data.split('_')
            cs_id = int(cs_id)
            
            password = buat_password()
            
            # ✅ FORMAT YANG DIMINTA:
            # user_ID - Asset
            # Password baru :
            message_to_cs = f"{user_id} - {asset}\nPassword baru : {password}"
            
            # Kirim password ke CS
            bot.send_message(cs_id, message_to_cs)
            
            # Update pesan di Captain
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ *RESET DISETUJUI*\n\n"
                     f"User: `{user_id}`\n"
                     f"Asset: `{asset}`\n"
                     f"Password: `{password}`\n\n"
                     f"✅ Sudah dikirim ke CS.",
                parse_mode='Markdown'
            )
            
            bot.answer_callback_query(call.id, "✅ Password dikirim")
            
        elif call.data.startswith('no_'):
            cs_id = int(call.data.split('_')[1])
            
            # Kirim notifikasi penolakan ke CS
            bot.send_message(cs_id, "Permintaan anda ditolak Captain !!")
            
            # Update pesan di Captain
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"❌ *REQUEST DITOLAK*\n\n"
                     f"CS sudah dinotifikasi.",
                parse_mode='Markdown'
            )
            
            bot.answer_callback_query(call.id, "❌ Request ditolak")
            
    except Exception as e:
        print(f"❌ Callback error: {e}")
        bot.answer_callback_query(call.id, "❌ Error")

# ========== START COMMAND ==========
@bot.message_handler(commands=['start', 'help'])
def start(m):
    bot.reply_to(m,
        "🤖 *Reset Password Bot*\n\n"
        "Kirim: `/reset UserID Asset`\n"
        "Contoh: `/reset kitty95 g20`\n\n"
        "Bisa kirim bukti transfer (foto) setelahnya.",
        parse_mode='Markdown'
    )

# ========== MAIN ==========
if __name__ == "__main__":
    print("=" * 50)
    print("🤖 BOT STARTING...")
    print(f"👑 Captain ID: {CAPTAIN_ID}")
    print("=" * 50)
    
    # Hapus webhook jika ada
    try:
        bot.remove_webhook()
        print("✅ Webhook cleared")
    except:
        pass
    
    # Polling
    bot.polling(none_stop=True, timeout=30)
