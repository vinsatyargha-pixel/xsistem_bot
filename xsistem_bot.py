import telebot
import random
import string
from telebot import types
import time

# CONFIG
TOKEN = "8087735462:AAGII-XvO3hJy3YgDd3b0vjiIHjnQCn4Ej4"
CAPTAIN_ID = 5720343562

bot = telebot.TeleBot(TOKEN)

# Fungsi password
def buat_password():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(10))

# Handler reset
@bot.message_handler(func=lambda m: m.text and '/reset' in m.text.lower())
def handle_reset(m):
    try:
        parts = m.text.split()
        if len(parts) < 3:
            bot.reply_to(m, "Format: /reset UserID Asset")
            return
        
        user_id = parts[1]
        asset = parts[2]
        
        # Kirim ke Captain
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Reset", callback_data=f"ok_{m.from_user.id}_{user_id}_{asset}"),
            types.InlineKeyboardButton("❌ Tolak", callback_data=f"no_{m.from_user.id}")
        )
        
        bot.send_message(
            CAPTAIN_ID,
            f"🔔 RESET\nCS: {m.from_user.full_name}\nUser: {user_id}\nAsset: {asset}",
            reply_markup=markup
        )
        
        bot.reply_to(m, "✅ Sent to Captain!")
        
    except Exception as e:
        print(f"Error: {e}")

# Handler callback
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        if call.data.startswith('ok_'):
            _, cs_id, user_id, asset = call.data.split('_')
            cs_id = int(cs_id)
            
            password = buat_password()
            
            # Kirim ke CS
            bot.send_message(cs_id, f"{user_id} - {asset}\nPassword baru : {password}")
            
            # Update pesan
            bot.edit_message_text("✅ Approved", call.message.chat.id, call.message.message_id)
            
        elif call.data.startswith('no_'):
            cs_id = int(call.data.split('_')[1])
            bot.send_message(cs_id, "Permintaan anda ditolak Captain !!")
            bot.edit_message_text("❌ Rejected", call.message.chat.id, call.message.message_id)
            
    except Exception as e:
        print(f"Callback error: {e}")

# Handler foto
@bot.message_handler(content_types=['photo'])
def handle_foto(m):
    try:
        bot.forward_message(CAPTAIN_ID, m.chat.id, m.message_id)
        bot.reply_to(m, "📸 Photo sent!")
    except:
        pass

# Main
if __name__ == "__main__":
    print("🤖 Bot starting...")
    
    # PASTIKAN HAPUS WEBHOOK
    try:
        bot.remove_webhook()
        print("✅ Webhook cleared")
    except:
        pass
    
    # Polling dengan retry
    while True:
        try:
            print("🔄 Polling...")
            bot.polling(none_stop=True, timeout=30)
        except Exception as e:
            print(f"⚠️ Error: {e}")
            print("🔄 Restarting in 5s...")
            time.sleep(5)
