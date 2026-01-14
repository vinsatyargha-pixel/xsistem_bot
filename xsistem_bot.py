import telebot
import random
import string
from telebot import types

# ========== CONFIG ==========
TOKEN = "YOUR_BOT_TOKEN_HERE"
CAPTAIN_GROUP_ID = -1001234567890  # Ganti dengan ID group captain

bot = telebot.TeleBot(TOKEN)

# ========== FUNGSI GENERATE PASSWORD ==========
def generate_password():
    """Generate password mix huruf besar, kecil, angka"""
    upper = random.choice(string.ascii_uppercase)
    lower = random.choice(string.ascii_lowercase)
    numbers = ''.join(random.choice(string.digits) for _ in range(8))
    password_chars = list(upper + lower + numbers)
    random.shuffle(password_chars)
    return ''.join(password_chars)

# ========== SIMPLE RESET FLOW ==========
@bot.message_handler(func=lambda message: '/reset' in message.text.lower() or 
                                           '/repass' in message.text.lower() or 
                                           '/repas' in message.text.lower())
def handle_reset_request(message):
    """Tangkap semua format reset dari CS"""
    cs_user = message.from_user
    text = message.text or ""
    
    # Extract UserID dan Asset dari berbagai format
    parts = text.strip().split()
    
    if len(parts) < 3:
        bot.reply_to(message, "Format: /reset UserID Asset\nContoh: /reset Appank07 G200M")
        return
    
    # Cari user_id dan asset (bisa di posisi mana saja)
    user_id = parts[1]  # Biasanya setelah /reset
    asset = parts[2] if len(parts) > 2 else "UNKNOWN"
    
    # Simpan data CS
    cs_data = {
        'id': cs_user.id,
        'name': cs_user.full_name,
        'username': cs_user.username
    }
    
    # Buat keyboard untuk captain
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_reset = types.InlineKeyboardButton("✅ Reset", callback_data=f"approve_{cs_user.id}_{user_id}_{asset}")
    btn_reject = types.InlineKeyboardButton("❌ Tolak", callback_data=f"reject_{cs_user.id}")
    markup.add(btn_reset, btn_reject)
    
    # Kirim ke group captain
    bot.send_message(
        CAPTAIN_GROUP_ID,
        f"🔔 *RESET REQUEST*\n\n"
        f"CS: {cs_user.full_name}\n"
        f"Request: {text}\n\n"
        f"Pilih tindakan:",
        reply_markup=markup,
        parse_mode='Markdown'
    )
    
    # Konfirmasi ke CS
    bot.reply_to(message, "✅ Request sudah diteruskan ke Captain!")

# ========== HANDLE PHOTO (BUKTI TRANSFER) ==========
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """Tangani bukti transfer yang dikirim setelah/before request"""
    # Cukup teruskan foto ke group captain
    bot.forward_message(CAPTAIN_GROUP_ID, message.chat.id, message.message_id)
    bot.reply_to(message, "📸 Bukti transfer telah diteruskan ke Captain!")

# ========== CAPTAIN APPROVAL ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))
def approve_request(call):
    """Captain pilih RESET"""
    data_parts = call.data.split('_')
    cs_user_id = int(data_parts[1])
    user_id = data_parts[2]
    asset = data_parts[3] if len(data_parts) > 3 else "UNKNOWN"
    
    # Generate password baru
    new_password = generate_password()
    
    # FORMAT SESUAI PERMINTAAN:
    # user_ID - Asset
    # Password baru :
    message_to_cs = f"{user_id} - {asset}\nPassword baru : {new_password}"
    
    # Kirim ke CS
    bot.send_message(cs_user_id, message_to_cs)
    
    # Update pesan di group captain
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"✅ RESET APPROVED untuk {user_id}\nPassword telah dikirim ke CS."
    )
    
    bot.answer_callback_query(call.id, "✅ Password dikirim ke CS")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_'))
def reject_request(call):
    """Captain pilih TOLAK"""
    cs_user_id = int(call.data.split('_')[1])
    
    # Kirim ke CS
    bot.send_message(cs_user_id, "Permintaan anda ditolak Captain !!")
    
    # Update pesan di group captain
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"❌ REQUEST DITOLAK\nCS sudah dinotifikasi."
    )
    
    bot.answer_callback_query(call.id, "❌ Request ditolak")

# ========== START ==========
@bot.message_handler(commands=['start', 'help'])
def start(message):
    help_text = """
    🤖 *SIMPLE RESET BOT*

    *CARA PAKAI:*
    Kirim: `/reset UserID Asset`
    
    *Contoh:*
    `/reset Appank07 G200M`
    `/reset Player123 G500M`
    
    *Format lainnya diterima:*
    `/repass UserID Asset`
    `/repas UserID - Asset`
    
    *Bisa kirim bukti transfer* (foto) sebelum/sesudah request.
    
    Request akan diteruskan ke Captain untuk approval.
    """
    bot.reply_to(message, help_text, parse_mode='Markdown')

# ========== RUN BOT ==========
if __name__ == "__main__":
    print("🤖 Simple Reset Bot Started!")
    print(f"📢 Captain Group: {CAPTAIN_GROUP_ID}")
    print("🔧 Ready to handle reset requests...")
    bot.polling(none_stop=True)
