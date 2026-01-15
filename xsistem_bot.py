import telebot
import random
import string
from telebot import types
from flask import Flask
import threading
import os

TOKEN = os.environ.get("TOKEN", "8087735462:AAGII-XvO3hJy3YgDd3b0vjiIHjnQCn4Ej4")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ========== BOT FUNCTIONS ==========
def buat_password():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(10))

# ========== /format COMMAND ==========
@bot.message_handler(commands=['format'])
def show_format(message):
    """Tampilkan contoh format yang benar"""
    format_contoh = (
        "📋 *CONTOH FORMAT YANG BENAR:*\n\n"
        "/repas ID ASSET\n"
        "BANK MEMBER\n"
        "BANK TUJUAN\n"
        "WALLET :\n"
        "OFFICER :\n\n"
        "───────────────\n"
        "*Contoh lengkap:*\n"
        "/repas kitty95 G20\n"
        "BRI\n"
        "BCA\n"
        "WALLET : DANA\n"
        "OFFICER : yoriko\n\n"
        "*Format alternatif juga bisa:*\n"
        "/reset kitty95 G20\n"
        "/repass kitty95-G20"
    )
    
    bot.reply_to(message, format_contoh, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text and any(
    cmd in m.text.lower() for cmd in ['/reset', '/repass', '/repas']
))
def handle_reset(message):
    try:
        text = message.text.strip()
        parts = text.split()
        
        if len(parts) < 3:
            bot.reply_to(message, 
                "❌ *Format salah!*\n\n"
                "Gunakan: `/reset ID ASSET`\n"
                "Contoh: `/reset kitty95 g20`\n\n"
                "Lihat format lengkap: /format",
                parse_mode='Markdown'
            )
            return
        
        user_id = parts[1]
        asset = parts[2]
        
        print(f"📩 Reset: {user_id} {asset} dari @{message.from_user.username}")
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Reset", callback_data=f"ok_{message.from_user.id}_{user_id}_{asset}"),
            types.InlineKeyboardButton("❌ Tolak", callback_data=f"no_{message.from_user.id}")
        )
        
        bot.reply_to(
            message,
            f"🔔 *RESET REQUEST*\n\n"
            f"👤 CS: {message.from_user.full_name}\n"
            f"📱 @{message.from_user.username or 'N/A'}\n"
            f"🆔 User: `{user_id}`\n"
            f"🎮 Asset: `{asset}`\n\n"
            f"**PILIH AKSI:**",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        print(f"❌ Error: {e}")
        bot.reply_to(message, "❌ Error!")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """IGNORE semua foto"""
    pass

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        if call.data.startswith('ok_'):
            _, cs_id, user_id, asset = call.data.split('_')
            cs_id = int(cs_id)
            
            password = buat_password()
            
            message_text = f"{user_id} - {asset}\nPassword baru : {password}"
            
            bot.send_message(
                call.message.chat.id,
                message_text,
                reply_to_message_id=call.message.reply_to_message.message_id
            )
            
            bot.edit_message_text(
                f"✅ *RESET DISETUJUI*\n\n"
                f"User: `{user_id}`\n"
                f"Asset: `{asset}`\n"
                f"Password: `{password}`\n\n"
                f"✅ Password sudah dikirim di chat.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
            
            bot.answer_callback_query(call.id, "✅ Password dikirim")
            
        elif call.data.startswith('no_'):
            cs_id = int(call.data.split('_')[1])
            
            bot.send_message(
                call.message.chat.id,
                "❌ Permintaan ditolak Captain !!",
                reply_to_message_id=call.message.reply_to_message.message_id
            )
            
            bot.edit_message_text(
                f"❌ *REQUEST DITOLAK*\n\n"
                f"CS sudah dinotifikasi.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
            
            bot.answer_callback_query(call.id, "❌ Ditolak")
            
    except Exception as e:
        print(f"❌ Callback error: {e}")
        bot.answer_callback_query(call.id, "❌ Error")

# ========== HELP COMMAND ==========
@bot.message_handler(commands=['help', 'start'])
def show_help(message):
    help_text = (
        "🤖 *X-SISTEM RESET BOT*\n\n"
        "*PERINTAH YANG TERSEDIA:*\n\n"
        "🔹 `/reset ID ASSET`\n"
        "   Contoh: `/reset kitty95 g20`\n\n"
        "🔹 `/repass ID ASSET`\n"
        "   (alternatif command)\n\n"
        "🔹 `/repas ID ASSET`\n"
        "   (alternatif command)\n\n"
        "🔹 `/format`\n"
        "   Tampilkan contoh format lengkap\n\n"
        "🔹 `/help`\n"
        "   Tampilkan pesan ini\n\n"
        "───────────────\n"
        "*CARA PAKAI:*\n"
        "1. CS kirim: `/reset kitty95 g20`\n"
        "2. Bot akan reply dengan tombol\n"
        "3. Captain pilih Reset/Tolak\n"
        "4. Password otomatis dikirim\n\n"
        "*Note:* Bisa kirim bukti transfer (foto) setelah command."
    )
    
    bot.reply_to(message, help_text, parse_mode='Markdown')

# ========== FLASK ROUTES ==========
@app.route('/')
def home():
    return '🤖 Bot is running!'

@app.route('/health')
def health():
    return 'OK', 200

# ========== RUN BOT IN THREAD ==========
def run_bot():
    print("🤖 Bot polling started...")
    bot.polling(none_stop=True)

# ========== MAIN ==========
if __name__ == "__main__":
    # Start bot in separate thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Start Flask for Render port
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Flask running on port {port}")
    print(f"🤖 Bot ready! Commands: /reset, /repass, /repas, /format")
    app.run(host='0.0.0.0', port=port)
