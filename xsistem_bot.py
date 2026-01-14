import telebot
import random
import string
import logging
from telebot import types

# ========== CONFIG ==========
TOKEN = "8087735462:AAGII-XvO3hJy3YgDd3b0vjiIHjnQCn4Ej4"
CAPTAIN_ID = 5720343562  # ⚠️ INI CHAT ID KAMU SENDIRI!

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

# ========== HANDLER RESET ==========
@bot.message_handler(func=lambda m: m.text and any(
    cmd in m.text.lower() for cmd in ['/reset', '/repass', '/repas']
))
def handle_reset(message):
    try:
        text = message.text.strip()
        parts = text.split()
        
        if len(parts) < 3:
            bot.reply_to(message, "❌ Format: `/reset UserID Asset`\nContoh: `/reset kitty95 g200m`", parse_mode='Markdown')
            return
        
        user_id = parts[1]
        asset = parts[2]
        
        logger.info(f"📩 Reset dari CS: {message.from_user.username} - {user_id} {asset}")
        
        # Keyboard untuk CAPTAIN (KAMU)
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_approve = types.InlineKeyboardButton(
            "✅ Reset", 
            callback_data=f"approve_{message.from_user.id}_{user_id}_{asset}"
        )
        btn_reject = types.InlineKeyboardButton(
            "❌ Tolak", 
            callback_data=f"reject_{message.from_user.id}"
        )
        markup.add(btn_approve, btn_reject)
        
        # Kirim ke CAPTAIN (KAMU)
        try:
            sent_msg = bot.send_message(
                CAPTAIN_ID,  # Langsung ke chat pribadi kamu!
                f"🔔 *RESET REQUEST*\n\n"
                f"👤 **CS:** {message.from_user.full_name}\n"
                f"📱 **Username:** @{message.from_user.username or 'N/A'}\n"
                f"🆔 **User ID:** `{user_id}`\n"
                f"🎮 **Asset:** `{asset}`\n\n"
                f"⏳ **Pilih aksi:**",
                reply_markup=markup,
                parse_mode='Markdown'
            )
            logger.info(f"✅ Request dikirim ke Captain (Message ID: {sent_msg.message_id})")
            
            # Konfirmasi ke CS
            bot.reply_to(message, "✅ *Request sudah dikirim ke Captain!*\nTunggu approval...", parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ Gagal mengirim ke Captain: {e}")
            bot.reply_to(message, "❌ Error mengirim ke Captain!", parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"❌ Error in handle_reset: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)}")

# ========== HANDLE PHOTO ==========
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """Forward bukti transfer ke CAPTAIN (KAMU)"""
    try:
        bot.forward_message(CAPTAIN_ID, message.chat.id, message.message_id)
        bot.reply_to(message, "📸 *Bukti transfer diteruskan ke Captain!*", parse_mode='Markdown')
        logger.info(f"📸 Photo forwarded from {message.from_user.username}")
    except Exception as e:
        logger.error(f"❌ Error forwarding photo: {e}")

# ========== CALLBACK HANDLER ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        if call.data.startswith('approve_'):
            # Format: approve_CS_ID_USER_ID_ASSET
            data = call.data.split('_')
            cs_id = int(data[1])
            user_id = data[2]
            asset = data[3]
            
            new_password = generate_password()
            logger.info(f"✅ Captain approve: {user_id} - {asset}")
            
            # FORMAT YANG DIMINTA:
            # user_ID - Asset
            # Password baru :
            message_text = f"{user_id} - {asset}\nPassword baru : {new_password}"
            
            # Kirim password ke CS
            bot.send_message(cs_id, message_text)
            
            # Update pesan di chat Captain
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ *RESET DISETUJUI*\n\n"
                     f"👤 User: `{user_id}`\n"
                     f"🎮 Asset: `{asset}`\n"
                     f"🔐 Password: `{new_password}`\n\n"
                     f"✅ Sudah dikirim ke CS.",
                parse_mode='Markdown'
            )
            
            bot.answer_callback_query(call.id, "✅ Password dikirim")
            
        elif call.data.startswith('reject_'):
            cs_id = int(call.data.split('_')[1])
            
            # Kirim ke CS
            bot.send_message(cs_id, "Permintaan anda ditolak Captain !!")
            
            # Update pesan di chat Captain
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"❌ *REQUEST DITOLAK*\n\n"
                     f"CS sudah dinotifikasi.",
                parse_mode='Markdown'
            )
            
            bot.answer_callback_query(call.id, "❌ Request ditolak")
            
    except Exception as e:
        logger.error(f"❌ Callback error: {e}")
        bot.answer_callback_query(call.id, "❌ Error")

# ========== START COMMAND ==========
@bot.message_handler(commands=['start', 'help'])
def start(message):
    help_text = """
    🤖 *SIMPLE RESET BOT*

    *CARA PAKAI:*
    Kirim: `/reset UserID Asset`
    
    *Contoh:*
    `/reset kitty95 g200m`
    `/reset player123 g500m`
    
    *Format lain:*
    `/repass UserID Asset`
    `/repas UserID - Asset`
    
    *Bisa kirim bukti transfer* (foto) setelahnya.
    
    Request akan langsung ke Captain untuk approval.
    """
    bot.reply_to(message, help_text, parse_mode='Markdown')

# ========== TEST BOT ==========
@bot.message_handler(commands=['test'])
def test_bot(message):
    """Test apakah bot jalan"""
    bot.reply_to(message, f"✅ Bot aktif!\nYour ID: {message.from_user.id}")

# ========== RUN BOT ==========
if __name__ == "__main__":
    print("=" * 50)
    print("🤖 SIMPLE RESET BOT STARTED!")
    print(f"⚡ Captain ID: {CAPTAIN_ID}")
    print(f"🔧 Log level: INFO")
    print("=" * 50)
    
    try:
        bot.polling(none_stop=True, timeout=30)
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        print("Restarting in 5 seconds...")
        import time
        time.sleep(5)
